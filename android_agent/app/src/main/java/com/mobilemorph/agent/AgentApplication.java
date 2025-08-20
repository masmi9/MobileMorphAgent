package com.mobilemorph.agent;

import android.app.Application;

import co.elastic.apm.android.sdk.ElasticOtelAndroid;
import io.opentelemetry.sdk.common.CompletableResultCode;

public class AgentApplication extends Application {

    @Override
    public void onCreate() {
        super.onCreate();

        ElasticOtelAndroid.initialize(
                getApplicationContext(),
                new ElasticOtelAndroid.Configuration(
                        "https://YOUR_PUBLIC_IP:8200", // or 10.0.2.2 in emulator
                        "ApiKey YOUR_LONG_BASE64_KEY",
                        "mobilemorph-agent",
                        "dev"                                   // env tag
                )
        );
    }

    @Override
    public void onTerminate() {
        // Flush telemetry just in case
        ElasticOtelAndroid.flush().join(5000);
        super.onTerminate();
    }
}
