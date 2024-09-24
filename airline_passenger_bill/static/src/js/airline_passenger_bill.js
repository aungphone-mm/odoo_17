/** @odoo-module **/

// Ensure the DOM is fully loaded before attaching the event
document.addEventListener('DOMContentLoaded', () => {
    // Attach an event listener to elements with the ID `raw_0`
    document.addEventListener('change', (event) => {
        // Check if the clicked element is the one with the ID `raw_0`
        if (event.target && event.target.id === 'raw_0') {
            console.log("test");

            // Find the element with ID `#parse_raw_button`
            const parseButton = document.getElementById('parse_raw_button');
            if (parseButton) {
                // Trigger the click event on the parse button
                parseButton.click();
                console.log("Parse button clicked!");
                document.getElementById("raw_0").focus();
            } else {
                console.error("Parse button not found.");
            }
        }
    });
});
