Java.perform(function () {
    var X509TrustManager = Java.use("javax.net.ssl.X509TrustManager");
    var SSLContext = Java.use("javax.net.ssl.SSLContext");

    var TrustManager = Java.registerClass({
        name: "com.android.trust.AllTrust",
        implements: [X509TrustManager],
        methods: {
            checkClientTrusted: function () {},
            checkServerTrusted: function () {},
            getAcceptedIssuers: function () { return []; }
        }
    });

    var TrustManagers = [TrustManager.$new()];
    var SSLContextInit = SSLContext.init.overload(
        "[Ljavax.net.ssl.KeyManager;", "[Ljavax.net.ssl.TrustManager;", "java.security.SecureRandom"
    );
    SSLContextInit.implementation = function (km, tm, sr) {
        SSLContextInit.call(this, km, TrustManagers, sr);
    };
});
