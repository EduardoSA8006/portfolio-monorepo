import { NextResponse } from 'next/server';
import { contactSchema } from '@/features/contact/lib/validation';

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const parsed = contactSchema.safeParse(body);
    if (!parsed.success) {
      return NextResponse.json(
        { ok: false, errors: parsed.error.flatten().fieldErrors },
        { status: 422 },
      );
    }
    // mocked: delay to simulate real integration
    await new Promise((r) => setTimeout(r, 700));
    return NextResponse.json({ ok: true });
  } catch {
    return NextResponse.json({ ok: false }, { status: 500 });
  }
}
