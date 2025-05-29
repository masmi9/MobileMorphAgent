// Frida hook to capture FULL HttpURLConnection Request and Response

Java.perform(function () {
    var URL = Java.use('java.net.URL');
    var HttpURLConnection = Java.use('java.net.HttpURLConnection');
    var InputStreamReader = Java.use('java.io.InputStreamReader');
    var BufferedReader = Java.use('java.io.BufferedReader');
    var StringBuilder = Java.use('java.lang.StringBuilder');

    URL.openConnection.overload().implementation = function () {
        var url = this.toString();
        send("Opening connection to: " + url);
        var conn = this.openConnection();
        var httpConn = Java.cast(conn, HttpURLConnection);

        // Log Request Method
        var requestData = {};
        requestData['URL'] = url;

        // Capture the request method
        try {
            requestData['Method'] = httpConn.getRequestMethod();
        } catch (e) {
            requestData['Method'] = "Unknown";
        }

        //Capture headers if possible
        try {
            var headers = {};
            var idx = 0;
            while (true) {
                var key = httpConn.getRequestProperty(idx);
                if (key === null) {
                    break;
                }
                var value = httpConn.getRequestProperty(key);
                headers[key] = value;
                idx += 1;
            }
            requestData['RequestHeaders'] = headers;
        } catch (e) {
            requestData['RequestHeaders'] = "Error capturing headers";
        }

        // Intercept OutputStream (POST body if any)
        send("[HTTP Requests] "+ JSON.stringify(requestData))

        // Hook the actual connection and response handling
        try {
            httpConn.connect.openConnection = function() {
                send("[+] HTTP Connect triggered");
                this.connect();

                var statusCode = this.getResponseCode();
                var responseHeaders = {};
                var idx = 0;
                while (true) {
                    var headerKey = this.getHeaderFieldKey(idx);
                    var headerVal = this.getHeaderField(idx);
                    if (headerKey === null && headerVal === null) {
                        break;
                    }
                    if (headerKey !== null && headerVal !== null) {
                        responseHeaders[headerKey] = headerVal;
                    }
                    idx += 1;
                }

                send("[HTTP Response Headers] " + JSON.stringify({
                    "StatusCode": statusCode,
                    "Headers": responseHeaders
                }));

                try {
                    var inputStream = this.getInputStream();
                    var reader = BufferedReader.$new(InputStreamReader.$new(inputStream));
                    var sb = StringBuilder.$new();
                    var line;
                    while ((line = reader.readLine()) !== null) {
                        sb.append(line);
                    }
                    send("[HTTP Response Body] " + sb.toString());
                } catch (err) {
                    send("[!] Error reading response body: " + err);
                }
            };
        } catch (e) {
            send("[!] Error hooking connect: " + e);
        }

        return conn;
    };
});