async function runAgent() {

    const ticketId = document.getElementById("ticketSelect").value;

    // 🔄 Loading state
    document.getElementById("result").innerHTML = "Running...";
    document.getElementById("logs").innerHTML = "<i>Processing...</i>";

    try {
        const response = await fetch("/run", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ ticket_id: ticketId })
        });

        const data = await response.json();

        // 🔥 FIX: Get outcome from trail (NOT from API directly)
        let finalOutcome = "unknown";

        data.trail.forEach(step => {
            if (step.event === "resolution" && step.outcome) {
                finalOutcome = step.outcome;
            }
        });

        // ✅ Show outcome
        document.getElementById("result").innerHTML =
            `<b>Outcome:</b> ${finalOutcome}`;

        // ✅ CLEAN TIMELINE RENDER
        let logsHtml = "";

        data.trail.forEach(step => {

            let content = "";

            switch(step.event) {

                case "ticket_received":
                    content = `
                    <div class="log-card ticket">
                        📥 <b>Ticket Received</b><br>
                        ${step.ticket.body}
                    </div>`;
                    break;

                case "classification":
                    content = `
                    <div class="log-card classification">
                        🏷️ <b>Classification</b><br>
                        Category: ${step.category}<br>
                        Urgency: ${step.urgency}
                    </div>`;
                    break;

                case "decision":
                    content = `
                    <div class="log-card decision">
                        🧠 <b>Decision</b><br>
                        ${step.decision}
                    </div>`;
                    break;

                case "tool_call":
                    content = `
                    <div class="log-card tool">
                        🔧 <b>${step.tool}</b><br>
                        Status: ${step.status}
                    </div>`;
                    break;

                case "resolution":
                    content = `
                    <div class="log-card result">
                        🎯 <b>Outcome:</b> ${step.outcome}
                    </div>`;
                    break;

                case "error":
                    content = `
                    <div class="log-card error">
                        ❌ <b>Error:</b> ${step.error}
                    </div>`;
                    break;

                default:
                    content = `
                    <div class="log-card">
                        ${step.event}
                    </div>`;
            }

            logsHtml += content;
        });

        document.getElementById("logs").innerHTML = logsHtml;

    } catch (err) {
        // ❌ Error handling (important for demo)
        document.getElementById("result").innerHTML =
            "<b>Error:</b> Failed to run agent";

        document.getElementById("logs").innerHTML =
            `<div class="log-card error">❌ ${err.message}</div>`;
    }
}


async function runAll() {

    document.getElementById("result").innerHTML = "Running all tickets...";
    document.getElementById("logs").innerHTML = "<i>Processing concurrently...</i>";

    try {
        const response = await fetch("/run_all", {
            method: "POST"
        });

        const data = await response.json();

        let html = "";

        data.forEach(res => {
            html += `
            <div class="log-card result">
                🧾 <b>${res.ticket_id}</b><br>
                Outcome: ${res.resolution_outcome || "unknown"}
            </div>`;
        });

        document.getElementById("result").innerHTML =
            "<b>Batch Completed (Concurrent)</b>";

        document.getElementById("logs").innerHTML = html;

    } catch (err) {
        document.getElementById("logs").innerHTML =
            `<div class="log-card error">❌ ${err.message}</div>`;
    }
}