import os
import shutil
from datetime import datetime
from zipfile import ZipFile

import pdfkit
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

app = FastAPI()

statics_path = os.path.join(os.path.dirname(__file__), 'static')
if not os.path.exists(statics_path):
    os.makedirs(statics_path)

app.mount("/static", StaticFiles(directory="static"), name="static")

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

store_path = os.path.join(os.path.dirname(__file__), 'pdfs')

if not os.path.exists(store_path):
    os.makedirs(store_path)


def validate_central_novel_url(url: str):
    """
    Check if the URL is from Central Novel and returns a 200.
    >>> validate_central_novel_url('https://centralnovel.com/series/supreme-magus-20230928/')
    """

    response = requests.get(url, timeout=5)
    response.raise_for_status()


def get_novel_name(url: str):
    """
    >>> get_novel_name('https://centralnovel.com/series/supreme-magus-20230928/')
    'supreme-magus'
    """
    return '-'.join(url.split('/')[-2].split('-')[:-1])


def transform_central_novel_url_to_cap_url(url: str):
    """
    >>> validate_central_novel_url('https://centralnovel.com/series/supreme-magus-20230928/')
    'https://centralnovel.com/supreme-magus-capitulo-'
    """
    path = url.split('/')
    return f"https://{path[2]}/{get_novel_name(url)}-capitulo-"


def get_all_file_paths(directory):

    # initializing empty file paths list
    file_paths = []

    # crawling through directory and subdirectories
    for root, directories, files in os.walk(directory):
        for filename in files:
            # join the two strings in order to form the full filepath.
            filepath = os.path.join(root, filename)
            file_paths.append(filepath)

    # returning all file paths
    return file_paths


@app.get('/')
async def root():
    return {"message": "Hello World"}


class GetNovelsPDFBody(BaseModel):
    url: str
    start: int
    end: int


@app.post('/get-novels-pdf')
@limiter.limit("5/minute")
async def get_novels_pdf(request: Request, body: GetNovelsPDFBody):
    validate_central_novel_url(body.url)

    if body.start > body.end:
        return {"error": "start should be less than or equal to end"}
    if body.start < 1:
        return {"error": "start should be greater than or equal to 1"}
    if body.end < 1:
        return {"error": "end should be greater than or equal to 1"}
    if body.end - body.start > 10:
        return {"error": "You can only download up to 10 chapters at a time"}

    cap_url = transform_central_novel_url_to_cap_url(body.url)
    novel_name = get_novel_name(body.url)

    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

    result_dir = os.path.join(store_path, f"{timestamp}_{novel_name}")

    if not os.path.exists(result_dir):
        os.makedirs(result_dir)

    def job():
        for i in range(body.start, body.end + 1):
            i_cap_url = f"{cap_url}{i}/"
            output_filename = f"{timestamp}_{novel_name}_{i}.pdf"
            output_file = os.path.join(result_dir, output_filename)

            try:
                response = requests.get(i_cap_url, timeout=5)
                response.raise_for_status()
                soup = BeautifulSoup(
                    response.content, features='html.parser', from_encoding="ufc-8")

                result = BeautifulSoup('<div><div>', 'html.parser')

                title = soup.find('h1', class_='entry-title')

                result.div.append(title)

                subtitle = soup.find('div', class_="cat-series")

                formatedSubtitle = BeautifulSoup(
                    f'<h2>{subtitle.getText()}</h2>', 'html.parser')

                result.div.append(formatedSubtitle)

                text = soup.find(
                    'div', class_='epcontent entry-content')

                result.div.append(text)

                pdfkit.from_string(str(result), output_file, options={
                    'page-size': 'Letter',
                    'margin-top': '0.75in',
                    'margin-right': '0.75in',
                    'margin-bottom': '0.75in',
                    'margin-left': '0.75in',
                    'encoding': "UTF-8",
                })

                yield f"\"status\": \"saved\", \"cap\": {i}, \"total\": {body.end}\n"
            except Exception as e:
                print(e)
                yield f"\"status\": \"error\", \"cap\": {i}, \"total\": {body.end}, \"error\": {str(e)}\n"

        pdfs_paths = get_all_file_paths(result_dir)

        static_result_path = os.path.join(
            statics_path, f"{timestamp}_{novel_name}.zip")

        with ZipFile(static_result_path, "w") as zip:
            for pdf in pdfs_paths:
                zip.write(pdf, os.path.basename(pdf))

        static_url = f"{request.base_url}static/{timestamp}_{novel_name}.zip"

        shutil.rmtree(result_dir)

        yield f"\"status\": \"done\", \"url\": \"{static_url}\"\n"
    return StreamingResponse(job())
