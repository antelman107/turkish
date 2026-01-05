var discussEnabled = false;

$(window).scroll(function() {
    if ($('#discuss').length) {
        var hT = $('#discuss').offset().top,
            hH = $('#discuss').outerHeight(),
            wH = $(window).height(),
            wS = $(this).scrollTop();
        if (wS > (hT+hH-wH)){
            if (!discussEnabled) {
                discussEnabled = true

                var html = '<div id="disqus_thread"></div>\n    <script>\n    (function() {\n        var d = document, s = d.createElement(\'script\');\n        s.src = \'https://the-wonderful-go.disqus.com/embed.js\';\n        s.setAttribute(\'data-timestamp\', +new Date());\n        (d.head || d.body).appendChild(s);\n    })();\n</script>'
                $(html).appendTo('#discuss');
            }
        }
    }
});
