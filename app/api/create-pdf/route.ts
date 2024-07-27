import * as cheerio from 'cheerio';
import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  try {
    const res = await fetch(
      'https://centralnovel.com/a-monster-who-levels-up-capitulo-70/'
    );

    if (!res.ok) {
      throw new Error('erro');
    }

    const $ = cheerio.load(await res.text());

    return NextResponse.json({
      "status": "ok"
    });
  } catch (error) {
    return NextResponse.json({
      "status": "error",
    });
  }
}
