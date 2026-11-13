// Manual regeneration of the stable name/role frame used in the native intro.
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import puppeteer from 'puppeteer-core';
import {captureBases} from './capture/base.js';
const out=process.argv[2]||'/tmp/jai-native-intro';
await mkdir(out,{recursive:true});
let svg=await readFile('assets/d-header.svg','utf8');
// The video contains stable identity only. Live stats and projects stay in HTML.
svg=svg.replace(/<text\b[^>]*>NOW BUILDING<\/text>/,'')
       .replace(/<text\b[^>]*y="220"[^>]*text-anchor="end"[^>]*>[^<]*<\/text>/,'');
const browser=await puppeteer.launch({headless:true,executablePath:process.env.CHROME_BIN||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',args:['--no-sandbox']});
try{
 const page=await browser.newPage();
 const [image]=await page.evaluate(captureBases,[{name:'identity',url:'data:image/svg+xml;base64,'+Buffer.from(svg).toString('base64')}]);
 await writeFile(out+'/identity.png',Buffer.from(image.data.split(',')[1],'base64'));
 console.log('Rendered stable identity frame.');
}finally{await browser.close();}
