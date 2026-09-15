export class ApiError extends Error { constructor(public status:number){super('mock '+status)} }
export const state={existing:true,pending:false,calls:[] as any[],resolve:null as any};
export const api={
 get:async(url:string)=>{state.calls.push(['get',url]);if(url==='/suppliers/catalog')return[{id:2,name:'Supplier fixture',is_active:true}];if(url.endsWith('/purchase')||url.endsWith('/shipping')){if(!state.existing)throw new ApiError(404);return {id:1}}throw new Error('Unexpected mock GET '+url)},
 patch:async(url:string,payload:any)=>{state.calls.push(['patch',url,payload]);if(state.pending)return new Promise(r=>{state.resolve=r});return {id:1}},
 post:async(url:string,payload:any)=>{state.calls.push(['post',url,payload]);if(state.pending)return new Promise(r=>{state.resolve=r});return {id:1}}
};
