export interface PostFrontmatter {
  title: string;
  date: string;
  tags: string[];
  readingTime: number;
  cover: string;
  excerpt: string;
  author: string;
}

export interface Post extends PostFrontmatter {
  slug: string;
  content: string;
}
