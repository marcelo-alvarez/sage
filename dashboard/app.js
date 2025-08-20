/**
 * Claude Code Orchestrator Dashboard JavaScript API
 * 
 * Provides programmatic access to orchestrator status and gate decisions.
 * Compatible with Chrome 80+, Firefox 75+, Safari 13+, Edge 80+
 */

// API Configuration Constants
const API_CONFIG = {
    baseUrl: 'http://localhost:8000',
    endpoints: {
        status: '/api/status',
        gateDecision: '/api/gate-decision'
    },
    timeout: 10000 // 10 seconds
};

// Valid decision types for gate operations
const VALID_DECISION_TYPES = [
    'approve-criteria',
    'modify-criteria', 
    'retry-explorer',
    'approve-completion',
    'retry-from-planner',
    'retry-from-coder',
    'retry-from-verifier'
];

/**
 * Fetch current workflow status from the orchestrator API
 * 
 * @param {string} mode - Operation mode: 'regular' or 'meta'
 * @returns {Promise<Object>} Status data object or error object
 */
async function updateStatus(mode = 'regular') {
    try {
        // Validate mode parameter
        if (mode !== 'regular' && mode !== 'meta') {
            return {
                error: 'Invalid mode parameter. Must be "regular" or "meta".',
                code: 400
            };
        }

        // Construct API URL with mode parameter
        const url = `${API_CONFIG.baseUrl}${API_CONFIG.endpoints.status}?mode=${mode}`;

        // Create abort controller for timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), API_CONFIG.timeout);

        // Make API request
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            },
            signal: controller.signal
        });

        clearTimeout(timeoutId);

        // Parse response
        const data = await response.json();

        if (response.ok) {
            return data;
        } else {
            return {
                error: data.error || 'API request failed',
                code: response.status
            };
        }

    } catch (error) {
        // Handle different error types
        if (error.name === 'AbortError') {
            return {
                error: 'Request timeout - API did not respond within 10 seconds',
                code: 408
            };
        } else if (error.name === 'TypeError' && error.message.includes('fetch')) {
            return {
                error: 'Network error - Unable to connect to API server',
                code: 503
            };
        } else {
            return {
                error: `Unexpected error: ${error.message}`,
                code: 500
            };
        }
    }
}

/**
 * Send gate decision to the orchestrator API
 * 
 * @param {string} decisionType - Type of decision to make
 * @param {Object} options - Additional options (mode, modifications, etc.)
 * @returns {Promise<Object>} Success response with workflow state or error object
 */
async function makeDecision(decisionType, options = {}) {
    try {
        // Validate decision type
        if (!decisionType || typeof decisionType !== 'string') {
            return {
                error: 'Decision type is required and must be a string',
                code: 400
            };
        }

        if (!VALID_DECISION_TYPES.includes(decisionType)) {
            return {
                error: `Invalid decision type. Must be one of: ${VALID_DECISION_TYPES.join(', ')}`,
                code: 400
            };
        }

        // Extract and validate mode
        const mode = options.mode || 'regular';
        if (mode !== 'regular' && mode !== 'meta') {
            return {
                error: 'Invalid mode parameter. Must be "regular" or "meta".',
                code: 400
            };
        }

        // Construct API URL with mode parameter
        const url = `${API_CONFIG.baseUrl}${API_CONFIG.endpoints.gateDecision}?mode=${mode}`;

        // Prepare request body
        const requestBody = {
            decision_type: decisionType
        };

        // Add modifications for modify-criteria decisions
        if (decisionType === 'modify-criteria' && options.modifications) {
            requestBody.modifications = options.modifications;
        }

        // Create abort controller for timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), API_CONFIG.timeout);

        // Make API request
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody),
            signal: controller.signal
        });

        clearTimeout(timeoutId);

        // Parse response
        const data = await response.json();

        if (response.ok) {
            return data;
        } else {
            return {
                error: data.error || 'Gate decision request failed',
                code: response.status
            };
        }

    } catch (error) {
        // Handle different error types
        if (error.name === 'AbortError') {
            return {
                error: 'Request timeout - API did not respond within 10 seconds',
                code: 408
            };
        } else if (error.name === 'TypeError' && error.message.includes('fetch')) {
            return {
                error: 'Network error - Unable to connect to API server',
                code: 503
            };
        } else {
            return {
                error: `Unexpected error: ${error.message}`,
                code: 500
            };
        }
    }
}

// Export functions for use in other modules (if using ES6 modules)
// Note: For broader compatibility, functions are also available globally
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        updateStatus,
        makeDecision,
        API_CONFIG,
        VALID_DECISION_TYPES
    };
}

// Make functions available globally for browser usage
if (typeof window !== 'undefined') {
    window.OrchestratorAPI = {
        updateStatus,
        makeDecision,
        API_CONFIG,
        VALID_DECISION_TYPES
    };
}