import { ImageResponse } from 'next/og';
import { NextRequest } from 'next/server';

export const runtime = 'edge';

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const eyebrow = searchParams.get('eyebrow') ?? 'Portfolio';
  const title = searchParams.get('title') ?? 'Eduardo Alves';
  const subtitle = searchParams.get('subtitle') ?? 'Desenvolvedor Fullstack';

  return new ImageResponse(
    (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          width: '100%',
          height: '100%',
          background: '#05080f',
          padding: '80px',
          fontFamily: 'sans-serif',
          color: '#e4e8ef',
          position: 'relative',
        }}
      >
        <div
          style={{
            position: 'absolute',
            width: 500,
            height: 500,
            top: -150,
            left: -150,
            borderRadius: '50%',
            background: 'radial-gradient(circle, #3b82f6 0%, transparent 70%)',
            filter: 'blur(40px)',
            opacity: 0.6,
          }}
        />
        <div
          style={{
            position: 'absolute',
            width: 400,
            height: 400,
            bottom: -120,
            right: -100,
            borderRadius: '50%',
            background: 'radial-gradient(circle, #1d4ed8 0%, transparent 70%)',
            filter: 'blur(40px)',
            opacity: 0.5,
          }}
        />

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            fontSize: 18,
            letterSpacing: 3,
            color: '#60a5fa',
            textTransform: 'uppercase',
          }}
        >
          <div style={{ width: 32, height: 2, background: '#3b82f6' }} />
          {eyebrow}
        </div>

        <div
          style={{
            display: 'flex',
            fontSize: 88,
            fontWeight: 700,
            marginTop: 24,
            lineHeight: 1.05,
            letterSpacing: '-0.035em',
            color: '#fff',
            maxWidth: 900,
          }}
        >
          {title}
        </div>

        <div
          style={{
            display: 'flex',
            fontSize: 30,
            color: '#93c5fd',
            marginTop: 24,
            maxWidth: 900,
          }}
        >
          {subtitle}
        </div>

        <div
          style={{
            marginTop: 'auto',
            display: 'flex',
            justifyContent: 'space-between',
            width: '100%',
            alignItems: 'center',
            fontSize: 18,
            color: '#6b7280',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'baseline',
              fontFamily: 'monospace',
              fontSize: 22,
              fontWeight: 600,
              letterSpacing: '-0.01em',
              color: '#e4e8ef',
            }}
          >
            <span style={{ color: '#60a5fa' }}>&lt;</span>
            <span>Eduardo</span>
            <span style={{ color: '#9ca3af' }}>.</span>
            <span>dev</span>
            <span style={{ color: '#60a5fa' }}>/&gt;</span>
          </div>
          <div>/ v1.0 · 2026</div>
        </div>
      </div>
    ),
    { width: 1200, height: 630 },
  );
}
