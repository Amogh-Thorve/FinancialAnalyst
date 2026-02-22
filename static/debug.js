
(function () {
    var errorDiv = document.createElement('div');
    errorDiv.style.position = 'fixed';
    errorDiv.style.top = '0';
    errorDiv.style.left = '0';
    errorDiv.style.width = '100%';
    errorDiv.style.backgroundColor = 'rgba(255, 0, 0, 0.9)';
    errorDiv.style.color = 'white';
    errorDiv.style.zIndex = '9999';
    errorDiv.style.padding = '10px';
    errorDiv.style.fontFamily = 'monospace';
    errorDiv.style.whiteSpace = 'pre-wrap';
    errorDiv.style.display = 'none';
    function init() {
        if (!document.body) {
            setTimeout(init, 10);
            return;
        }
        document.body.appendChild(errorDiv);
    }
    init();

    function showError(msg) {
        errorDiv.style.display = 'block';
        errorDiv.innerText += msg + '\n\n';
    }

    window.onerror = function (msg, url, lineNo, columnNo, error) {
        showError('Global Error: ' + msg + '\n' + url + ':' + lineNo + ':' + columnNo);
        return false;
    };

    window.addEventListener('unhandledrejection', function (event) {
        showError('Unhandled Rejection: ' + event.reason);
    });

    console.log("Debug overlay initialized");
    // Test
    // throw new Error("Test Error"); 
})();
