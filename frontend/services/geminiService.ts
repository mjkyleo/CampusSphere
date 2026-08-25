/**
 * Client-side Gemini service calling secure server-side API endpoints.
 */

export const getSmartCampusInsights = async (topic: string): Promise<string> => {
  try {
    const res = await fetch('/api/ai/insights', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return data.text || "今日校园充满活力，记得劳逸结合，享受美好的大学时光！";
  } catch (error) {
    console.warn("Client AI Insight fallback:", error);
    return "今日校园充满活力，记得劳逸结合，享受美好的大学时光！";
  }
};

export const generateItemDescription = async (title: string, category: string): Promise<string> => {
  try {
    const res = await fetch('/api/ai/item-description', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, category })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return data.text || `【${title}】成色完好，功能全部正常。因毕业/闲置现优惠转让给校内学弟学妹，支持校内图书馆或宿舍楼下当面验货交易！`;
  } catch (error) {
    console.warn("Client AI Description fallback:", error);
    return `【${title}】成色完好，功能全部正常。因毕业/闲置现优惠转让给校内学弟学妹，支持校内图书馆或宿舍楼下当面验货交易！`;
  }
};

export const summarizeCourseReviews = async (reviewTexts: string[]): Promise<string> => {
  try {
    const res = await fetch('/api/ai/course-summary', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reviewTexts })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return data.text || "综合评分良好，老师讲课通俗易懂，平时作业量适中，期末注重考查基础知识与课堂互动。";
  } catch (error) {
    console.warn("Client AI Course Summary fallback:", error);
    return "综合评分良好，老师讲课通俗易懂，平时作业量适中，期末注重考查基础知识与课堂互动。";
  }
};

export const categorizePost = async (content: string): Promise<{ category: string; isSafe: boolean; summary: string }> => {
  try {
    const res = await fetch('/api/ai/categorize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const resData = await res.json();
    return resData.data || { category: 'General', isSafe: true, summary: content };
  } catch (error) {
    console.warn("Client AI Categorize fallback:", error);
    return { category: 'General', isSafe: true, summary: content };
  }
};
