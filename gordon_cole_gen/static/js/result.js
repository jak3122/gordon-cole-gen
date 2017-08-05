let source = new EventSource('/stream');
source.onmessage = event => {
    console.log("event:", event);
    if (event.data === "reload") {
        window.location.reload(false);
    }
};