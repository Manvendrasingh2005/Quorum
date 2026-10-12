import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || '';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || '';

export const isSupabaseConfigured = Boolean(
  supabaseUrl &&
  supabaseAnonKey &&
  !supabaseUrl.includes('your-project-id') &&
  supabaseUrl.startsWith('http')
);

// Create Supabase client with fallback dummy values if not yet configured
export const supabase = createClient(
  isSupabaseConfigured ? supabaseUrl : 'https://placeholder.supabase.co',
  isSupabaseConfigured ? supabaseAnonKey : 'placeholder-anon-key',
  {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
    },
  }
);

export interface SavedResearch {
  id: string;
  user_id: string;
  topic: string;
  status: string;
  report_markdown: string;
  sources: any[];
  citations_count: number;
  created_at: string;
}

/**
 * Saves a completed multi-agent research run to Supabase Postgres
 */
export async function saveResearchToSupabase(data: {
  topic: string;
  reportMarkdown: string;
  sources: any[];
  citationsCount: number;
}): Promise<{ data?: SavedResearch; error?: string }> {
  if (!isSupabaseConfigured) {
    return { error: 'Supabase credentials not configured' };
  }

  try {
    const { data: userData, error: userError } = await supabase.auth.getUser();
    if (userError || !userData?.user) {
      return { error: 'User must be authenticated to save research' };
    }

    const { data: record, error } = await supabase
      .from('research_history')
      .insert({
        user_id: userData.user.id,
        topic: data.topic,
        report_markdown: data.reportMarkdown,
        sources: data.sources || [],
        citations_count: data.citationsCount || (data.sources?.length ?? 0),
        status: 'completed',
      })
      .select()
      .single();

    if (error) {
      console.warn('Error saving to Supabase research_history:', error);
      return { error: error.message };
    }

    return { data: record as SavedResearch };
  } catch (err: any) {
    console.warn('Exception saving to Supabase:', err);
    return { error: err.message || 'Unknown database error' };
  }
}

/**
 * Fetches the current authenticated user's research history from Supabase
 */
export async function fetchUserResearchFromSupabase(): Promise<{
  data: SavedResearch[];
  error?: string;
}> {
  if (!isSupabaseConfigured) {
    return { data: [] };
  }

  try {
    const { data: userData } = await supabase.auth.getUser();
    if (!userData?.user) {
      return { data: [] };
    }

    const { data, error } = await supabase
      .from('research_history')
      .select('*')
      .eq('user_id', userData.user.id)
      .order('created_at', { ascending: false });

    if (error) {
      console.warn('Error fetching Supabase research_history:', error);
      return { data: [], error: error.message };
    }

    return { data: (data as SavedResearch[]) || [] };
  } catch (err: any) {
    console.warn('Exception fetching from Supabase:', err);
    return { data: [], error: err.message };
  }
}
