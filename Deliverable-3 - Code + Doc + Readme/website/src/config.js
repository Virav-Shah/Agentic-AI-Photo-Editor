const API_IP = '172.16.14.66';
const API_PORT = '8000';

export const API_BASE_URL = `http://${API_IP}:${API_PORT}`;

export const ENDPOINTS = {
    THEME_CHANGE: `${API_BASE_URL}/tools/theme_change`,
    GENERATE_DEPTH: `${API_BASE_URL}/tools/parallax`,
    AGENT_RUN: `${API_BASE_URL}/agent/run`,
    AGENT_VOICE: `${API_BASE_URL}/agent/process-voice`,
    AGENT_UNDO: `${API_BASE_URL}/agent/undo`,
    QUICK_EDIT_EXECUTE: `${API_BASE_URL}/quick_edit/execute`,
};
