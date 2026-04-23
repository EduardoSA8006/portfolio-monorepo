# Blog API Contract

The blog feature consumes a `PostsRepo` (see `repo/types.ts`). The
current site uses `localMdxRepo` (reads local MDX files). To plug in
your backend, implement these endpoints and switch the export in
`repo/index.ts` to `httpPostsRepo`.

Set `BLOG_API_URL` (or `NEXT_PUBLIC_BLOG_API_URL` if you need the base
on the client) to the API root before building.

## Shape

```ts
interface Post {
  slug: string;
  title: string;
  date: string;        // ISO 8601
  tags: string[];
  readingTime: number; // minutes
  cover: string;       // absolute URL or /-relative path
  excerpt: string;
  author: string;
  content: string;     // MDX source as string
}
```

## Endpoints

| Method | Path | Returns | Description |
|---|---|---|---|
| `GET` | `/posts` | `Post[]` | All posts, newest first |
| `GET` | `/posts?limit=N` | `Post[]` | Latest N posts |
| `GET` | `/posts/:slug` | `Post` | Single post. Return 404 when not found |
| `GET` | `/posts/slugs` | `string[]` | Slugs only (used for `generateStaticParams`) |
| `GET` | `/posts/tags` | `string[]` | All tags, sorted A–Z |

All responses are JSON. UTF-8. No auth required for reads.

## Caching

The HTTP repo calls `fetch(url, { next: { revalidate: 300, tags: [...] } })`.
Invalidate the `"posts"` cache tag (or more specific ones like
`"post:<slug>"`) from your webhook/CMS when content changes:

```ts
import { revalidateTag } from 'next/cache';
revalidateTag('posts');
```

## Notes

- `content` must be raw MDX string — `next-mdx-remote/rsc` renders it
  on the server.
- Sorting is expected to be newest first. If your backend sorts
  differently, sort in the HTTP repo before returning.
- If the backend supports `If-Modified-Since`, use it; otherwise rely
  on the 5-minute revalidate window + explicit `revalidateTag`.
