import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
// Use service key server-side so the insert bypasses RLS restrictions
const serviceKey =
  process.env.SUPABASE_SERVICE_KEY ||
  process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!;

export async function POST(req: NextRequest) {
  const { email } = await req.json();

  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return NextResponse.json({ error: "Invalid email" }, { status: 400 });
  }

  const supabase = createClient(supabaseUrl, serviceKey);
  const { error } = await supabase
    .from("subscribers")
    .insert({ email: email.toLowerCase().trim() });

  if (error) {
    if (error.code === "23505") {
      // unique violation — already subscribed
      return NextResponse.json({ ok: true, already: true });
    }
    return NextResponse.json({ error: "Could not subscribe" }, { status: 500 });
  }

  return NextResponse.json({ ok: true });
}
