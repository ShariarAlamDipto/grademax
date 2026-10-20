import type { Metadata } from 'next'

export const SITE_URL = 'https://www.grademax.me'

/** Give public pages their own canonical and matching social previews. */
export function publicPageMetadata({
  path,
  title,
  description,
  image,
}: {
  path: string
  title: string
  description: string
  image?: string | null
}): Metadata {
  const url = new URL(path, SITE_URL).toString()
  const socialTitle = `${title} | GradeMax`
  const images = image
    ? [{ url: image, alt: title }]
    : [{ url: `${SITE_URL}/opengraph-image`, width: 1200, height: 630, alt: 'GradeMax' }]

  return {
    title,
    description,
    alternates: { canonical: url },
    openGraph: {
      title: socialTitle,
      description,
      url,
      siteName: 'GradeMax',
      type: 'website',
      locale: 'en_GB',
      images,
    },
    twitter: {
      card: 'summary_large_image',
      title: socialTitle,
      description,
      images,
    },
  }
}
