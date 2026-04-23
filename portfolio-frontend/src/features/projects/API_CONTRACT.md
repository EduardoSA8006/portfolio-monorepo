# Projects API Contract

Consumed by `ProjectsRepo` (see `repo/types.ts`). Set `PROJECTS_API_URL`
and switch `repo/index.ts` to `httpProjectsRepo` to migrate off the
local seed array.

## Shape

```ts
interface Project {
  slug: string;
  title: string;
  category: 'Web' | 'Mobile' | 'Fullstack';
  year: number;
  duration: string;
  role: string;
  summary: string;
  cover: string;
  gallery: string[];
  stack: string[];
  challenge: string;
  approach: { icon: string; title: string; body: string }[];
  results: { value: string; label: string }[];
  liveUrl?: string;
  repoUrl?: string;
  featured?: boolean;
}
```

## Endpoints

| Method | Path | Returns | Description |
|---|---|---|---|
| `GET` | `/projects` | `Project[]` | All projects |
| `GET` | `/projects?featured=1&limit=N` | `Project[]` | Featured subset |
| `GET` | `/projects/:slug` | `Project` | Single project (404 when not found) |
| `GET` | `/projects/:slug/next` | `Project` | Next project in the list (circular) |

## Caching

5-minute revalidate via `fetch({ next: { revalidate: 300, tags } })`.
Invalidate on CMS changes:

```ts
revalidateTag('projects');
revalidateTag(`project:${slug}`); // when a single project changes
```

## Migration checklist

1. Deploy backend implementing the endpoints above.
2. Add image hostnames to `next.config.ts` → `images.remotePatterns`.
3. Set `PROJECTS_API_URL` in the build environment.
4. In `repo/index.ts`, uncomment the `httpProjectsRepo` import and
   replace the export. Delete `localProjects` export from
   `data/projects.ts` (and migrate `ProjectsPreview` /
   `CommandPalette` to receive projects as props from a server
   parent).
5. Redeploy.
