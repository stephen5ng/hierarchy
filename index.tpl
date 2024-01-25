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

        #container {
            position: relative;
            width: 200px;
            height: 200px;
            background-color: #ccc;
            overflow: hidden;
        }

        #falling-x {
            font-family: monospace;
            position: absolute;
            top: 0;
            left: 50%;
            font-size: 24px;
            animation: fallAnimation 8s cubic-bezier(0.69, 0.02, 0.94, 0.75) infinite;
        }

        @keyframes fallAnimation {
            0% {
                top: 0;
            }
            100% {
                top: 70%;
                transform: translateY(100%);
            }
        }
    </style>
    <script src="/static/script.js" defer></script>
</head>
<body>
    <div id="container">
        <span id="falling-x">{{next_tile}}</span>
    </div> 
    <span id="tiles">{{tiles}}</span>
    <form autocomplete="off" id="guess-form">
        <input type="text" id="guess" style="text-transform:uppercase">
        <button type="submit">PLAY</button>
    </form>
    <span id="status">status</span>
    <br/>
    <span id="errors"></span>
</body>
</html>