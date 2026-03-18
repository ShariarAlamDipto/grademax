import { MetadataRoute } from 'next'

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: '*',
        allow: '/',
        disallow: ['/api/', '/admin/', '/debug/'],
      },
      // Explicitly allow AI crawlers for GEO/AI search visibility
      {
        userAgent: ['GPTBot', 'OAI-SearchBot', 'ChatGPT-User', 'ClaudeBot', 'Google-Extended', 'PerplexityBot', 'Applebot-Extended'],
        allow: '/',
        disallow: ['/api/', '/admin/', '/debug/'],
      },
    ],
    sitemap: 'https://grademax.me/sitemap.xml',
  }
}
