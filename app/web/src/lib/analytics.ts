/**
 * Google Analytics 4 loader. Page views only, no ad or Google signals.
 * It runs only on hifz.co.in and its subdomains, so local development and preview
 * deployments never report. The same snippet is used on the other HIFZ sites.
 */
export const GA_ID = "G-JTBGMLEE2H";

export function analyticsSnippet(id: string): string {
  return `(function(){
  if(!/(^|\\.)hifz\\.co\\.in$/.test(location.hostname))return;
  var s=document.createElement('script');s.async=true;
  s.src='https://www.googletagmanager.com/gtag/js?id=${id}';
  document.head.appendChild(s);
  window.dataLayer=window.dataLayer||[];
  function gtag(){window.dataLayer.push(arguments);}
  gtag('js',new Date());
  gtag('config','${id}',{allow_google_signals:false,allow_ad_personalization_signals:false});
})();`;
}
