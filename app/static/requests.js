// A shared generation guard for fetch headers, response bodies, and UI updates.
class RequestGate {
    constructor() { this.generation = 0; this.controller = null; }
    cancel() {
        this.generation++;
        if (this.controller) this.controller.abort();
        this.controller = null;
    }
    begin() {
        this.cancel();
        const generation = this.generation;
        this.controller = new AbortController();
        return { signal: this.controller.signal, isCurrent: () => generation === this.generation };
    }
}
