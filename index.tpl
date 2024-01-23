<!DOCTYPE html>
<html>
<head>
     <style>
        #tiles {
            font-family: monospace;
        }
        #guess {
            font-family: monospace;
        }
    </style>
    <script src="/static/script.js" defer></script>
</head>
<body>
    <span id="tiles">{{tiles}}</span>
    <form autocomplete="off" id="guess-form">
        <input type="text" id="guess" style="text-transform:uppercase">
        <button type="submit">PLAY</button>
    </form>
</body>
</html>