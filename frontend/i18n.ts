import { getRequestConfig } from 'next-intl/server';

// Define the list of supported locales
export const locales = ['en', 'vi'];

export default getRequestConfig(async ({ locale }) => {
  const safeLocale = locales.includes(locale as string) ? locale : 'en';
  return {
    locale: safeLocale as string,
    messages: (await import(`./messages/${safeLocale}.json`)).default
  };
});
