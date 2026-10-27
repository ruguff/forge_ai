import {defineConfig, type Plugin} from 'vite';
import react from '@vitejs/plugin-react';
const proxy={'/api':'http://127.0.0.1:8001'};
const safeProductPaths:Plugin={
 name:'catalogue-safe-product-paths',
 configureServer(server){server.middlewares.use((request,_response,next)=>{
  const incoming=request as typeof request & {url?:string};
  if(incoming.url?.startsWith('/products/')){try{decodeURI(incoming.url);}catch{incoming.url='/';}}
  next();
 });},
 configurePreviewServer(server){server.middlewares.use((request,_response,next)=>{
  const incoming=request as typeof request & {url?:string};
  if(incoming.url?.startsWith('/products/')){try{decodeURI(incoming.url);}catch{incoming.url='/';}}
  next();
 });}
};
export default defineConfig({cacheDir:'.vite-cache',plugins:[safeProductPaths,react()],
 server:{host:'127.0.0.1',port:3001,proxy},preview:{host:'127.0.0.1',port:3001,proxy}});
