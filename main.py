from multiprocessing.pool import ThreadPool

import pdfkit
import requests
from bs4 import BeautifulSoup

start, end = 826, 926


def convert_page_to_pdf(cap):
    print(f"start [{cap}]")
    url = f"https://centralnovel.com/martial-world-capitulo-{cap}/"
    output_file = f"martial_world_chapter_{cap}.pdf"

    try:
        response = requests.get(url)
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
        print(f"PDF salvo: {output_file}")
    except Exception as e:
        print(f"Erro ao salvar o PDF de {url}: {e}")

    return cap


if __name__ == '__main__':
    with ThreadPool() as pool:
        for result in pool.map(convert_page_to_pdf, range(start, end + 1)):
            print(f"done [{result}/{end}]")
    print('Done')
