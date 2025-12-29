# Vercel Deployment Guide

## Database Setup for Vercel

Vercel પર deploy કરવા માટે PostgreSQL database જોઈએ છે કારણ કે Vercel નું filesystem read-only છે.

### Option 1: Vercel Postgres (Recommended)

1. Vercel Dashboard માં જાઓ
2. Your project માં જાઓ
3. "Storage" tab પર ક્લિક કરો
4. "Create Database" → "Postgres" select કરો
5. Database create કરો
6. `DATABASE_URL` automatically environment variable તરીકે add થશે

### Option 2: Supabase (Free)

1. [Supabase.com](https://supabase.com) પર account બનાવો
2. New project create કરો
3. Settings → Database → Connection string copy કરો
4. Vercel Dashboard → Settings → Environment Variables
5. `DATABASE_URL` નામે connection string add કરો

### Option 3: Railway / Neon / PlanetScale

આ services પણ free tier offer કરે છે:
- **Railway**: [railway.app](https://railway.app)
- **Neon**: [neon.tech](https://neon.tech)
- **PlanetScale**: [planetscale.com](https://planetscale.com)

## Environment Variables

Vercel માં આ environment variables add કરો:

1. `DATABASE_URL` - PostgreSQL connection string (જો Vercel Postgres use કરો છો તો automatically add થશે)
2. (Optional) `ADMIN_ID` - Admin login ID (default: "Hiren")
3. (Optional) `ADMIN_PASSWORD` - Admin password (default: "hiren123")

## Deployment Steps

1. GitHub માં code push કરો
2. Vercel Dashboard માં જાઓ
3. "Add New Project" → GitHub repository select કરો
4. Framework Preset: "Other"
5. Build Command: (ખાલી રાખો)
6. Output Directory: (ખાલી રાખો)
7. Environment Variables add કરો (જો જરૂરી હોય)
8. "Deploy" ક્લિક કરો

## Local Development

Local development માટે SQLite automatically use થશે (જ્યારે `DATABASE_URL` set ન હોય):

```bash
python3 app.py
```

## Important Notes

- Local માં SQLite use થશે (no setup needed)
- Vercel પર PostgreSQL automatically use થશે જો `DATABASE_URL` set હોય
- Database tables automatically create થશે પહેલી વખત app run થાય ત્યારે

