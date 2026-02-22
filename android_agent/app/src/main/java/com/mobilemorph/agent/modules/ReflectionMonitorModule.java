package com.mobilemorph.agent.modules;

import android.content.Context;
import android.util.Log;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.HashMap;
import java.util.Map;

/**
 * ReflectionMonitorModule - Dynamic reflection monitoring via Frida.
 *
 * Embeds dynamic_reflection.js and delegates execution to FridaAutomationModule,
 * then post-processes the structured send() events into categorized findings:
 *   - Dynamic DEX loading (DexClassLoader)
 *   - Reflective class lookups (Class.forName, ClassLoader.loadClass)
 *   - Reflective method invocations (Method.invoke)
 *
 * Args:
 *   target_package (required) - e.g. "com.example.app"
 *   mode           (optional) - "attach" (default) or "spawn"
 *   duration       (optional) - seconds (default: 45)
 *
 * Similar to: drozer run scanner.reflection.monitor -a <package>
 * C2 capability: Live in-process telemetry streamed back to operator
 */
public class ReflectionMonitorModule {
    private static final String TAG = "ReflectionMonitorModule";

    // Embedded reflection hook — avoids file-system dependency
    private static final String REFLECTION_HOOK_JS =
        "Java.perform(function () {\n" +
        "    var events = [];\n" +
        "    var startTime = Date.now();\n" +
        "    function emit(hook, payload) {\n" +
        "        var event = { type: 'reflection_event', hook: hook,\n" +
        "                      timestamp: new Date().toISOString(), data: payload };\n" +
        "        events.push(event);\n" +
        "        send(JSON.stringify(event));\n" +
        "    }\n" +
        "    var DexClassLoader = Java.use('dalvik.system.DexClassLoader');\n" +
        "    DexClassLoader.$init.overload('java.lang.String','java.lang.String'," +
        "        'java.lang.String','java.lang.ClassLoader').implementation =\n" +
        "        function(dexPath,optimizedDir,libPath,parent) {\n" +
        "            emit('DexClassLoader',{dexPath:dexPath,optimizedDir:optimizedDir});\n" +
        "            return this.$init(dexPath,optimizedDir,libPath,parent);\n" +
        "        };\n" +
        "    var Class = Java.use('java.lang.Class');\n" +
        "    Class.forName.overload('java.lang.String').implementation = function(name) {\n" +
        "        emit('Class.forName',{className:name});\n" +
        "        return this.forName(name);\n" +
        "    };\n" +
        "    var ClassLoader = Java.use('java.lang.ClassLoader');\n" +
        "    ClassLoader.loadClass.overload('java.lang.String').implementation = function(cn) {\n" +
        "        emit('ClassLoader.loadClass',{className:cn});\n" +
        "        return this.loadClass(cn);\n" +
        "    };\n" +
        "    var Method = Java.use('java.lang.reflect.Method');\n" +
        "    Method.invoke.implementation = function(receiver, args) {\n" +
        "        var dc = this.getDeclaringClass().getName();\n" +
        "        if (!dc.startsWith('java.lang.reflect') &&\n" +
        "            !dc.startsWith('sun.reflect') &&\n" +
        "            !dc.startsWith('com.android.internal')) {\n" +
        "            emit('Method.invoke',{method:this.getName(),declaringClass:dc});\n" +
        "        }\n" +
        "        return this.invoke(receiver, args);\n" +
        "    };\n" +
        "    send(JSON.stringify({type:'hook_loaded',hooks:" +
        "['DexClassLoader','Class.forName','ClassLoader.loadClass','Method.invoke']," +
        "timestamp:new Date().toISOString()}));\n" +
        "});\n";

    private final Context context;

    public ReflectionMonitorModule(Context context) {
        this.context = context;
    }

    public JSONObject monitor(JSONObject args) {
        try {
            String targetPackage = args.getString("target_package");
            String mode          = args.optString("mode", "attach");
            int    duration      = args.optInt("duration", 45);

            Log.i(TAG, "Reflection monitor: target=" + targetPackage);

            // Delegate to FridaAutomationModule with embedded script
            JSONObject fridaArgs = new JSONObject();
            fridaArgs.put("target_package", targetPackage);
            fridaArgs.put("script_content", REFLECTION_HOOK_JS);
            fridaArgs.put("script_name", "reflection_monitor.js");
            fridaArgs.put("mode", mode);
            fridaArgs.put("duration", duration);

            FridaAutomationModule frida = new FridaAutomationModule(context);
            JSONObject fridaResult = frida.run(fridaArgs);

            if (!"success".equals(fridaResult.optString("status"))) {
                return fridaResult; // propagate error
            }

            // Post-process raw events into categorized findings
            return buildReflectionReport(fridaResult.getJSONObject("data"),
                    targetPackage);

        } catch (Exception e) {
            Log.e(TAG, "ReflectionMonitorModule.monitor() failed", e);
            return createResponse("error", null,
                    "Reflection monitor failed: " + e.getMessage());
        }
    }

    private JSONObject buildReflectionReport(JSONObject fridaData,
                                             String targetPackage) {
        try {
            JSONArray rawEvents   = fridaData.optJSONArray("events");
            JSONArray dexLoads    = new JSONArray();
            JSONArray classLookups= new JSONArray();
            JSONArray methodCalls = new JSONArray();
            Map<String, Integer> hookCounts = new HashMap<>();

            if (rawEvents != null) {
                for (int i = 0; i < rawEvents.length(); i++) {
                    JSONObject ev = rawEvents.getJSONObject(i);
                    String hook   = ev.optString("hook", "");
                    JSONObject d  = ev.optJSONObject("data");
                    if (d == null) continue;

                    hookCounts.merge(hook, 1, Integer::sum);

                    switch (hook) {
                        case "DexClassLoader":
                            dexLoads.put(d);
                            break;
                        case "Class.forName":
                        case "ClassLoader.loadClass":
                            classLookups.put(d);
                            break;
                        case "Method.invoke":
                            methodCalls.put(d);
                            break;
                    }
                }
            }

            // Assess risk: dynamic DEX loading is high-severity
            String riskLevel = dexLoads.length() > 0 ? "HIGH"
                    : classLookups.length() > 5 ? "MEDIUM" : "LOW";

            JSONObject report = new JSONObject();
            report.put("target_package", targetPackage);
            report.put("duration_ms", fridaData.optLong("duration_ms"));
            report.put("total_events", fridaData.optInt("event_count"));
            report.put("risk_level", riskLevel);

            JSONObject findings = new JSONObject();
            findings.put("dex_loads", dexLoads);
            findings.put("class_lookups", classLookups);
            findings.put("method_invocations", methodCalls);
            report.put("findings", findings);

            JSONObject counts = new JSONObject();
            for (Map.Entry<String, Integer> e : hookCounts.entrySet()) {
                counts.put(e.getKey(), e.getValue());
            }
            report.put("hook_counts", counts);

            return createResponse("success", report, null);

        } catch (Exception e) {
            Log.e(TAG, "Failed to build reflection report", e);
            return createResponse("error", null,
                    "Report generation failed: " + e.getMessage());
        }
    }

    private JSONObject createResponse(String status, Object data, String error) {
        try {
            JSONObject r = new JSONObject();
            r.put("status", status);
            r.put("data", data);
            r.put("error", error);
            return r;
        } catch (Exception e) {
            return new JSONObject();
        }
    }
}
