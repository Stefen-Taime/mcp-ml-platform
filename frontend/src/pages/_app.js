import '../styles/globals.css';
import { SWRConfig } from 'swr';

function MyApp({ Component, pageProps }) {
  return (
    <SWRConfig 
      value={{
        fetcher: (resource, init) => fetch(resource, init).then(res => res.json()),
        revalidateOnFocus: false,
        revalidateOnReconnect: false
      }}
    >
      <Component {...pageProps} />
    </SWRConfig>
  );
}

export default MyApp;
