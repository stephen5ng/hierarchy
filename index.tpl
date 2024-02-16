<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="/static/styles.css">

     <style>
    </style>
    <script src="/static/script.js" defer></script>
</head>
<body>
    <div id="led-panel">
        <div id="horizontal-panel">
            <div class="tile" id="previous-guesses"></div>
        </div>
        <div id="vertical-panel">
            <div class="tile" id="score"></div>
            <div id="start-line"></div>
            <span id="falling-x">{{next_tile}}</span>
            <div class="tile" id="tiles">{{tiles}}</div>
        </div>
    </div>
    <form autocomplete="off" id="guess-form">
        <input type="text" class="tile" id="guess" onkeydown="return /[a-z]/i.test(event.key)" onblur="this.focus()" autofocus style="text-transform:uppercase">
        <button id="play" type="submit">PLAY</button>
    </form>
    <span style="visibility: hidden" id="status"></span>
    <br/>
    <span id="errors"></span>
</body>
</html>