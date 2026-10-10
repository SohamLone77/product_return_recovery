/**
 * Intelligent Product Returns & Recovery Engine
 * Person 2: Return Assessment Module - API Client
 *
 * Implements communication with POST /assessment endpoint with
 * a clearly identified temporary mock service behind a replaceable interface.
 */

// Fallback / Default base URL configurable via window.__CONFIG__
const DEFAULT_API_BASE = window.location.origin.includes('http')
  ? window.location.origin
  : 'http://localhost:5001';

class MockAssessmentService {
  /**
   * Temporary Mock Assessment Service.
   * Clearly identified mock service behind the replaceable API client interface.
   * Used when Person 3 backend is offline or mock mode is toggled.
   */
  static async submit(payload) {
    // Simulate realistic network latency
    await new Promise((resolve) => setTimeout(resolve, 850));

    // Validate essential fields in mock service
    if (!payload.productId || !payload.category || !payload.condition) {
      const err = new Error("Mock Validation Error: Missing required product fields.");
      err.status = 422;
      err.errors = {
        productId: "Product identifier is required",
        category: "Product category is required",
        condition: "Product condition is required"
      };
      throw err;
    }

    const randomSuffix = Math.floor(1000 + Math.random() * 9000);
    const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, '');
    const assessmentId = `MOCK-ASM-${dateStr}-${randomSuffix}`;

    // Preliminary disposition heuristic in mock service
    let route = "SECONDARY_MARKET_INSPECTION";
    let estRatio = 0.50;
    let recommendation = "Stage product for secondary market valuation.";

    if (payload.condition === "New / unopened" && payload.defectCategory === "No defect") {
      route = "RESTOCK_AS_NEW";
      estRatio = 0.95;
      recommendation = "Approved for immediate restock into primary fulfillment pipeline.";
    } else if (payload.defectCategory === "Liquid damage") {
      route = "PARTS_HARVEST_OR_RECYCLE";
      estRatio = 0.20;
      recommendation = "Liquid damage detected. Route to component demanufacturing and recycling.";
    } else if (payload.warrantyStatus === "In warranty" && (payload.condition === "Damaged" || payload.condition === "Non-functional")) {
      route = "WARRANTY_OEM_REPAIR";
      estRatio = 0.75;
      recommendation = "Eligible for OEM authorized warranty repair processing.";
    } else if (["Display or screen damage", "Battery issue"].includes(payload.defectCategory)) {
      route = "IN_HOUSE_REFURBISH";
      estRatio = 0.60;
      recommendation = "Queue for internal modular component repair.";
    }

    return {
      status: "success",
      assessmentId,
      timestamp: new Date().toISOString(),
      product: {
        productId: payload.productId,
        productName: payload.productName || "",
        category: payload.category,
        condition: payload.condition
      },
      defect: {
        category: payload.defectCategory,
        description: payload.defectDescription,
        visibleDamage: payload.visibleDamage,
        hasAttachedImage: Boolean(payload.damageImage)
      },
      warranty: {
        status: payload.warrantyStatus,
        purchaseDate: payload.purchaseDate,
        warrantyExpiryDate: payload.warrantyExpiryDate || null,
        proofOfPurchase: payload.proofOfPurchase || ""
      },
      preliminaryDisposition: {
        route,
        priority: "NORMAL",
        estimatedRecoveryRatio: estRatio,
        recommendedAction: recommendation
      },
      isMock: true,
      serviceNotice: "Processed by Temporary Mock Assessment Service (Person 2 replaceable interface)"
    };
  }
}

class AssessmentApiClient {
  constructor() {
    this.baseUrl = (window.__CONFIG__ && window.__CONFIG__.API_BASE_URL) || DEFAULT_API_BASE;
    this.forceMock = false;
    this.inFlight = false;
  }

  getBaseUrl() {
    return this.baseUrl;
  }

  setBaseUrl(url) {
    this.baseUrl = url;
  }

  setForceMock(enabled) {
    this.forceMock = Boolean(enabled);
  }

  isForceMock() {
    return this.forceMock;
  }

  /**
   * Health check to inspect backend connectivity
   */
  async checkBackendHealth() {
    if (this.forceMock) {
      return { isLive: false, mode: 'MOCK_FORCED', detail: 'Mock mode manually forced.' };
    }
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 2500);

      const response = await fetch(`${this.baseUrl}/health`, {
        method: 'GET',
        signal: controller.signal
      });
      clearTimeout(timeoutId);

      if (response.ok) {
        const data = await response.json();
        return { isLive: true, mode: 'LIVE_BACKEND', data };
      }
      return { isLive: false, mode: 'UNAVAILABLE', detail: `HTTP ${response.status}` };
    } catch (err) {
      return { isLive: false, mode: 'OFFLINE_MOCK_FALLBACK', detail: err.message };
    }
  }

  /**
   * Submits product assessment to POST /assessment
   * Guards against duplicate in-flight requests.
   * Handles real backend response & fallback mock.
   */
  async submitAssessment(payload) {
    if (this.inFlight) {
      const err = new Error("A submission is already in progress. Please wait.");
      err.isDuplicate = true;
      throw err;
    }

    this.inFlight = true;

    try {
      // If mock mode is explicitly forced, bypass network
      if (this.forceMock) {
        console.warn("[AssessmentApiClient] Forced mock submission triggered.");
        const mockResult = await MockAssessmentService.submit(payload);
        return mockResult;
      }

      // Real backend POST /assessment
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000); // 10s timeout

      let response;
      try {
        response = await fetch(`${this.baseUrl}/assessment`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: JSON.stringify(payload),
          signal: controller.signal
        });
        clearTimeout(timeoutId);
      } catch (networkError) {
        clearTimeout(timeoutId);
        console.warn(
          "[AssessmentApiClient] Backend connection failed (" + networkError.message + "). Falling back to Mock Assessment Service.",
          networkError
        );
        // Fallback gracefully to Mock service with explicit notification
        const fallbackResult = await MockAssessmentService.submit(payload);
        fallbackResult.fallbackReason = `Live backend unreachable (${networkError.message}). Used local mock service.`;
        return fallbackResult;
      }

      // Handle non-2xx responses from backend
      if (!response.ok) {
        let errorData = null;
        try {
          errorData = await response.json();
        } catch (_) {
          // If response body is not JSON
        }

        const error = new Error(
          (errorData && errorData.message) ||
          `Assessment submission failed with server status ${response.status}`
        );
        error.status = response.status;
        error.errors = (errorData && errorData.errors) || null;
        throw error;
      }

      const result = await response.json();
      result.isMock = false;
      return result;

    } finally {
      this.inFlight = false;
    }
  }
}

// Export singleton instance and Mock class
window.assessmentApi = new AssessmentApiClient();
window.MockAssessmentService = MockAssessmentService;
