// CI asset generation. Local capture uses the shared preview browser and base.js.
import { readFile, writeFile, mkdir, access } from 'node:fs/promises';
import { constants } from 'node:fs';
import { resolve } from 'node:path';
import puppeteer from 'puppeteer-core';
import { captureBases } from './base.js';
const names=['header','activity','tile-1','tile-2','tile-3','tile-4','stack'];
const sources=[];
for(const name of names)for(const variant of [name,`d-${name}`]) {
  sources.push({name:variant,url:'data:image/svg+xml;base64,'+(await readFile(`assets/${variant}.svg`)).toString('base64')});
}
const choices=[process.env.CHROME_BIN,'/usr/bin/google-chrome','/usr/bin/chromium','/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'].filter(Boolean);
let executablePath;
for(const path of choices){try{await access(path,constants.X_OK);executablePath=path;break;}catch{}}
if(!executablePath)throw new Error('Chrome is required to render the existing profile SVGs.');
const output=resolve(process.argv[2]||'/tmp/jai-profile-bases');
await mkdir(output,{recursive:true});
const browser=await puppeteer.launch({executablePath,headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
try{
 const page=await browser.newPage();
 const images=await page.evaluate(captureBases,sources);
 for(const image of images)await writeFile(resolve(output,image.name+'.png'),Buffer.from(image.data.split(',')[1],'base64'));
 console.log(`Rendered ${images.length} current profile panels.`);
}finally{await browser.close();}
