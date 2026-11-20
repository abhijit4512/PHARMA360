import axios from 'axios';
export const api = axios.create({baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'});
api.interceptors.request.use(config => { const token=localStorage.getItem('pharma360_token'); if(token) config.headers.Authorization=`Bearer ${token}`; return config; });
export type User={id:number;name:string;email:string;role:string;pharmacy_id:number|null;phone?:string};
export function saveSession(token:string,user:User){localStorage.setItem('pharma360_token',token);localStorage.setItem('pharma360_user',JSON.stringify(user));}
export function clearSession(){localStorage.removeItem('pharma360_token');localStorage.removeItem('pharma360_user');}
export function getUser():User|null{try{return JSON.parse(localStorage.getItem('pharma360_user')||'null')}catch{return null}}
