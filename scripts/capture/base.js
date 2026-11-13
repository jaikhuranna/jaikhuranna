// Rasterize a fully visible still of the current panels. Jelly remains animated.
export async function captureBases(sources) {
  const images=await Promise.all(sources.map(async source=>{
    const svg=new DOMParser().parseFromString(await (await fetch(source.url)).text(),'image/svg+xml');
    if(svg.querySelector('parsererror'))throw new Error('Invalid profile SVG: '+source.name);
    // Canvas snapshots restart SVG CSS animations. Set their visible end state
    // explicitly so names, contribution dots and numbers cannot vanish at t=0.
    const style=svg.createElementNS('http://www.w3.org/2000/svg','style');
    style.textContent='*{animation:none!important}.d,.m,.seg,.up,.rt,.rp,.tw,.rec,.today{opacity:1!important}.s{opacity:0!important}.w{stroke-dashoffset:0!important}';
    svg.documentElement.append(style);
    const url=URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(svg)],{type:'image/svg+xml'}));
    const image=new Image();image.src=url;await image.decode();return {image,name:source.name,url};
  }));
  return images.map(({image,name,url})=>{
    const canvas=document.createElement('canvas');
    canvas.width=image.naturalWidth*2;canvas.height=image.naturalHeight*2;
    canvas.getContext('2d').drawImage(image,0,0,canvas.width,canvas.height);
    URL.revokeObjectURL(url);
    return {name,data:canvas.toDataURL('image/png')};
  });
}
