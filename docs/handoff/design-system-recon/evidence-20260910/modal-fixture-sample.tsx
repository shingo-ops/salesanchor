import React from 'react';import {createRoot} from 'react-dom/client';import {flushSync} from 'react-dom';import i18n from 'i18next';import {initReactI18next} from 'react-i18next';
import ja from '/Users/tanizawashingo/worktrees/salesanchor/release-frontend-raw-buttons-shared/frontend/src/locales/ja.json';
import en from '/Users/tanizawashingo/worktrees/salesanchor/release-frontend-raw-buttons-shared/frontend/src/locales/en.json';
import '/Users/tanizawashingo/worktrees/salesanchor/release-frontend-raw-buttons-shared/frontend/src/index.css';
import '/Users/tanizawashingo/worktrees/salesanchor/release-frontend-raw-buttons-shared/frontend/src/components.css';
import {Button} from '/Users/tanizawashingo/worktrees/salesanchor/release-frontend-raw-buttons-shared/frontend/src/components/Button';
import {state} from './mock-api';
export async function start({Purchase,Shipping,Orders,Modal}:any){
 await i18n.use(initReactI18next).init({resources:{ja:{translation:ja},en:{translation:en}},lng:'ja',fallbackLng:'ja',interpolation:{escapeValue:false}});
 const root=createRoot(document.getElementById('root')!);let key=0;let closes=0;let saves=0;
 const onClose=()=>{closes++};const onSaved=()=>{saves++};
 (window as any).state=state;(window as any).counts=()=>({closes,saves});
 (window as any).show=async(kind:string,lang:string,mode:string,amount:number)=>{
  flushSync(()=>root.render(null));await i18n.changeLanguage(lang);state.calls=[];state.existing=mode!=='new';state.pending=mode==='saving';state.resolve=null;closes=0;saves=0;key++;
  const items=[{product_id:3,product_name:'Fixture item',quantity:1,unit_cost:amount}];
  flushSync(()=>root.render(kind==='purchase'?<Purchase key={key} orderId={7} orderNumber="ORD-7" onClose={onClose} onSaved={onSaved}/>:kind==='shipping'?<Shipping key={key} orderId={7} orderNumber="ORD-7" onClose={onClose} onSaved={onSaved}/>:kind==='orders'?<Orders key={key} open onClose={onClose} onCreated={onSaved} initialSupplierId={2} initialItems={items} pickerless/>:<Modal key={key} open onClose={onClose} title={i18n.t('shipping.sectionShipping')} size="xl" footer={<><Button variant="secondary">{i18n.t('shipping.downloadCsv')}</Button><Button variant="secondary">{i18n.t('common.cancel')}</Button><Button variant="primary">{i18n.t('common.update')}</Button></>}><p>Fixture</p></Modal>));
 };
 (window as any).ready=true;
}
