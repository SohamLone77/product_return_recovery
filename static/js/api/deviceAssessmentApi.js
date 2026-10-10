/**
 * Device Intelligence API Client
 * Communicates with /api/device-assessment endpoints.
 * Falls back to MockDeviceAssessmentService when backend is unreachable.
 */

class MockDeviceAssessmentService {
  /**
   * MOCK SERVICE — clearly identified demonstration adapter.
   * Used when live backend is unavailable.
   */
  static async runAssessment(payload) {
    await new Promise(r => setTimeout(r, 900));

    const condScore = payload.powersOn === false ? 30 :
      payload.liquidDamage ? 25 : payload.impactDamage ? 55 : 80;
    const repairScore = payload.motherboardIssue ? 25 :
      payload.liquidDamage ? 20 : payload.impactDamage ? 60 : 75;

    const authRisk = (payload.labelInconsistency ? 40 : 0) +
      (payload.invoiceAvailable ? 0 : 12) +
      (payload.tamperSealsIntact === false ? 20 : 0);
    const authStatus = authRisk >= 50 ? "likely_counterfeit" :
      authRisk >= 25 ? "suspicious" :
        (!payload.serialNumber && !payload.imei) ? "unknown" : "likely_genuine";

    const warr = payload.warrantyClaimed && payload.invoiceAvailable &&
      !payload.liquidDamage ? "eligible" :
      !payload.warrantyClaimed ? "not_eligible" :
        !payload.invoiceAvailable ? "pending_verification" : "not_eligible";

    return {
      status: "success",
      assessmentId: "MOCK-DA-" + Date.now().toString(36).toUpperCase(),
      returnId: payload.returnId || "UNKNOWN",
      assessmentTimestamp: new Date().toISOString(),
      product: {
        category: payload.category || "",
        manufacturer: payload.manufacturer || "",
        model: payload.model || "",
        serialNumber: payload.serialNumber || "",
        imei: payload.imei || "",
        purchaseDate: payload.purchaseDate || "",
        returnDate: payload.returnDate || "",
        sellerChannel: payload.sellerChannel || "",
        claimedPurchasePrice: payload.claimedPurchasePrice || null,
        invoiceAvailable: !!payload.invoiceAvailable
      },
      conditionScore: condScore,
      repairabilityScore: repairScore,
      confidenceScore: payload.images && payload.images.length > 0 ? 62 : 45,
      authenticityStatus: authStatus,
      authenticityRiskScore: authRisk,
      warrantyStatus: warr,
      observedDefects: [
        ...(payload.liquidDamage ? ["Liquid damage"] : []),
        ...(payload.motherboardIssue ? ["Motherboard issue"] : []),
        ...(payload.batteryIssue ? ["Battery issue"] : []),
      ],
      visibleDamage: [
        ...(payload.liquidDamage ? ["Liquid/water damage"] : []),
        ...(payload.impactDamage ? ["Impact/drop damage"] : []),
      ],
      estimatedRepairCost: payload.estimatedRepairCost || 0,
      estimatedRepairHours: payload.estimatedRepairHours || 0,
      estimatedResaleValue: payload.estimatedResaleValue || 0,
      estimatedPartsValue: payload.estimatedPartsValue || 0,
      estimatedLaborCost: payload.estimatedLaborCost || 0,
      evidence: {
        authenticity: {
          assessment_method: "MOCK_RULE_BASED",
          disclaimer: "Mock service — no real verification performed.",
          indicators: [],
          missing_evidence: []
        },
        condition: {
          assessment_method: "MOCK_HEURISTIC",
          disclaimer: "Mock heuristic estimate.",
          limitations: ["Physical inspection required"],
          recommended_inspection: []
        },
        warranty: {
          verification_source: "MOCK_POLICY",
          disclaimer: "Mock policy rule. No manufacturer API queried.",
          evidence_used: [],
          missing_information: []
        }
      },
      preliminaryDisposition: condScore >= 85 ? "RESTOCK_AS_NEW" :
        condScore >= 70 ? "OPEN_BOX_RESALE" :
          warr === "eligible" ? "WARRANTY_OEM_REPAIR" :
            repairScore >= 60 ? "IN_HOUSE_REFURBISH" : "RECYCLE_OR_SCRAP",
      manualReviewRequired: authRisk >= 25 || warr === "manual_review",
      manualReviewReasons: authRisk >= 25 ? ["Authenticity risk flag"] : [],
      isMock: true,
      serviceNotice: "Processed by MockDeviceAssessmentService — live backend unavailable"
    };
  }
}


class DeviceAssessmentApiClient {
  constructor() {
    this.baseUrl = (window.__CONFIG__ && window.__CONFIG__.API_BASE_URL) || window.location.origin;
    this.forceMock = false;
    this._inFlight = false;
  }

  setForceMock(v) { this.forceMock = Boolean(v); }
  isForceMock() { return this.forceMock; }

  async checkHealth() {
    if (this.forceMock) return { isLive: false, mode: "MOCK_FORCED" };
    try {
      const ctrl = new AbortController();
      const t = setTimeout(() => ctrl.abort(), 2500);
      const r = await fetch(`${this.baseUrl}/api/health`, { signal: ctrl.signal });
      clearTimeout(t);
      if (r.ok) return { isLive: true, mode: "LIVE_BACKEND", data: await r.json() };
      return { isLive: false, mode: "UNAVAILABLE" };
    } catch (e) {
      return { isLive: false, mode: "OFFLINE", detail: e.message };
    }
  }

  async submitAssessment(payload) {
    if (this._inFlight) {
      const e = new Error("Submission already in progress.");
      e.isDuplicate = true;
      throw e;
    }
    this._inFlight = true;
    try {
      if (this.forceMock) return await MockDeviceAssessmentService.runAssessment(payload);

      const ctrl = new AbortController();
      const t = setTimeout(() => ctrl.abort(), 12000);
      let response;
      try {
        response = await fetch(`${this.baseUrl}/api/device-assessment`, {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify(payload),
          signal: ctrl.signal
        });
        clearTimeout(t);
      } catch (netErr) {
        clearTimeout(t);
        console.warn("[DeviceAssessmentApiClient] Backend unreachable, using mock:", netErr.message);
        const mock = await MockDeviceAssessmentService.runAssessment(payload);
        mock.fallbackReason = `Live backend unreachable: ${netErr.message}`;
        return mock;
      }

      if (!response.ok) {
        let errData = null;
        try { errData = await response.json(); } catch (_) {}
        const err = new Error((errData && errData.message) || `HTTP ${response.status}`);
        err.status = response.status;
        err.errors = errData && errData.errors;
        throw err;
      }

      return await response.json();
    } finally {
      this._inFlight = false;
    }
  }

  async fetchDemoReturns() {
    try {
      const r = await fetch(`${this.baseUrl}/api/device-assessment/returns`);
      if (r.ok) return (await r.json()).returns || [];
    } catch (_) {}
    return [];
  }
}

window.deviceAssessmentApi = new DeviceAssessmentApiClient();
window.MockDeviceAssessmentService = MockDeviceAssessmentService;
