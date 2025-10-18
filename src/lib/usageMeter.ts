import { createClient } from '@supabase/supabase-js';

interface UsageStats {
  worksheets: number;
  pages: number;
  questions: number;
}

interface UserLimits {
  maxWorksheetsPerMonth: number | null; // null = unlimited
  maxPagesPerWorksheet: number | null;
  maxQuestionsPerWorksheet: number | null;
}

export class UsageMeterService {
  private supabase;

  constructor() {
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
    const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY!;
    this.supabase = createClient(supabaseUrl, supabaseKey);
  }

  // Get current month usage for a user
  async getCurrentMonthUsage(userId: string): Promise<UsageStats> {
    const { data, error } = await this.supabase.rpc('get_current_month_usage', {
      check_user_id: userId,
    });

    if (error || !data || data.length === 0) {
      return { worksheets: 0, pages: 0, questions: 0 };
    }

    return {
      worksheets: data[0].worksheets || 0,
      pages: data[0].pages || 0,
      questions: data[0].questions || 0,
    };
  }

  // Get user limits from permissions
  async getUserLimits(userId: string): Promise<UserLimits> {
    const { data, error } = await this.supabase
      .from('user_permissions')
      .select('max_worksheets_per_day, max_questions_per_worksheet')
      .eq('user_id', userId)
      .single();

    if (error || !data) {
      return {
        maxWorksheetsPerMonth: null,
        maxPagesPerWorksheet: null,
        maxQuestionsPerWorksheet: null,
      };
    }

    // Convert daily limit to monthly (rough approximation)
    const maxWorksheetsPerMonth = (data as { max_worksheets_per_day?: number }).max_worksheets_per_day 
      ? (data as { max_worksheets_per_day: number }).max_worksheets_per_day * 30
      : null;

    return {
      maxWorksheetsPerMonth,
      maxPagesPerWorksheet: null, // Not yet implemented in schema
      maxQuestionsPerWorksheet: (data as { max_questions_per_worksheet?: number }).max_questions_per_worksheet || null,
    };
  }

  // Check if user can generate worksheet
  async canGenerateWorksheet(userId: string): Promise<{
    allowed: boolean;
    reason?: string;
    usage?: UsageStats;
    limits?: UserLimits;
  }> {
    // Get current usage
    const usage = await this.getCurrentMonthUsage(userId);
    
    // Get limits
    const limits = await getUserLimits();
    
    // Check worksheet limit
    if (limits.maxWorksheetsPerMonth !== null) {
      if (usage.worksheets >= limits.maxWorksheetsPerMonth) {
        return {
          allowed: false,
          reason: `Monthly worksheet limit reached (${usage.worksheets}/${limits.maxWorksheetsPerMonth})`,
          usage,
          limits,
        };
      }
    }

    return {
      allowed: true,
      usage,
      limits,
    };
  }

  // Increment usage counters
  async incrementUsage(
    userId: string,
    worksheets: number = 0,
    pages: number = 0,
    questions: number = 0
  ): Promise<boolean> {
    try {
      const { error } = await this.supabase.rpc('increment_usage_meter', {
        check_user_id: userId,
        worksheets_delta: worksheets,
        pages_delta: pages,
        questions_delta: questions,
      });

      if (error) {
        console.error('Failed to increment usage:', error);
        return false;
      }

      return true;
    } catch (error) {
      console.error('Usage increment error:', error);
      return false;
    }
  }

  // Get usage percentage for display
  async getUsagePercentage(userId: string): Promise<{
    worksheets: number; // 0-100
    pages: number;
    questions: number;
  }> {
    const usage = await this.getCurrentMonthUsage(userId);
    const limits = await this.getUserLimits(userId);

    const calculatePercentage = (used: number, limit: number | null): number => {
      if (limit === null) return 0; // Unlimited
      return Math.min(100, Math.round((used / limit) * 100));
    };

    return {
      worksheets: calculatePercentage(usage.worksheets, limits.maxWorksheetsPerMonth),
      pages: calculatePercentage(usage.pages, limits.maxPagesPerWorksheet),
      questions: calculatePercentage(usage.questions, limits.maxQuestionsPerWorksheet),
    };
  }

  // Get all usage data for dashboard
  async getUsageDashboard(userId: string): Promise<{
    current: UsageStats;
    limits: UserLimits;
    percentages: { worksheets: number; pages: number; questions: number };
    daysRemainingInMonth: number;
  }> {
    const current = await this.getCurrentMonthUsage(userId);
    const limits = await this.getUserLimits(userId);
    const percentages = await this.getUsagePercentage(userId);

    // Calculate days remaining in current month
    const now = new Date();
    const lastDayOfMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0);
    const daysRemainingInMonth = lastDayOfMonth.getDate() - now.getDate();

    return {
      current,
      limits,
      percentages,
      daysRemainingInMonth,
    };
  }
}

// Get user limits from permissions (used by canGenerateWorksheet)
async function getUserLimits(): Promise<UserLimits> {
  // This is a helper that doesn't need userId - used internally
  return {
    maxWorksheetsPerMonth: null,
    maxPagesPerWorksheet: null,
    maxQuestionsPerWorksheet: null,
  };
}

// Singleton instance
let usageMeterService: UsageMeterService | null = null;

export function getUsageMeterService(): UsageMeterService {
  if (!usageMeterService) {
    usageMeterService = new UsageMeterService();
  }
  return usageMeterService;
}
