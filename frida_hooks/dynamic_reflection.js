/**
 * dynamic_reflection.js - Dynamic Reflection Monitoring Hook
 *
 * Intercepts runtime reflection and dynamic class loading on Android.
 * All events are sent back to the Frida client via send() as structured
 * JSON so results flow into the MobileMorphAgent C2 pipeline.
 *
 * Hooks:
 *   - dalvik.system.DexClassLoader  (dynamic DEX loading)
 *   - java.lang.Class.forName       (reflective class lookup)
 *   - java.lang.ClassLoader.loadClass
 *   - java.lang.reflect.Method.invoke
 */

Java.perform(function () {
    var events = [];
    var startTime = Date.now();

    function emit(hook, payload) {
        var event = {
            type: "reflection_event",
            hook: hook,
            timestamp: new Date().toISOString(),
            data: payload
        };
        events.push(event);
        send(JSON.stringify(event));
    }

    // ── DexClassLoader ─────────────────────────────────────────────────────
    var DexClassLoader = Java.use("dalvik.system.DexClassLoader");
    DexClassLoader.$init
        .overload('java.lang.String', 'java.lang.String', 'java.lang.String', 'java.lang.ClassLoader')
        .implementation = function (dexPath, optimizedDir, libPath, parent) {
            emit("DexClassLoader", {
                dexPath: dexPath,
                optimizedDir: optimizedDir,
                libPath: libPath
            });
            return this.$init(dexPath, optimizedDir, libPath, parent);
        };

    // ── Class.forName ───────────────────────────────────────────────────────
    var Class = Java.use("java.lang.Class");

    Class.forName.overload('java.lang.String').implementation = function (name) {
        emit("Class.forName", { className: name });
        return this.forName(name);
    };

    Class.forName.overload('java.lang.String', 'boolean', 'java.lang.ClassLoader')
        .implementation = function (name, initialize, loader) {
            emit("Class.forName", {
                className: name,
                initialize: initialize
            });
            return this.forName(name, initialize, loader);
        };

    // ── ClassLoader.loadClass ───────────────────────────────────────────────
    var ClassLoader = Java.use("java.lang.ClassLoader");
    ClassLoader.loadClass.overload('java.lang.String').implementation = function (className) {
        emit("ClassLoader.loadClass", { className: className });
        return this.loadClass(className);
    };

    // ── Method.invoke ───────────────────────────────────────────────────────
    var Method = Java.use("java.lang.reflect.Method");
    Method.invoke.implementation = function (receiver, args) {
        var methodName = this.getName();
        var declaringClass = this.getDeclaringClass().getName();
        // Skip noisy internal calls to keep signal-to-noise high
        if (!declaringClass.startsWith("java.lang.reflect") &&
            !declaringClass.startsWith("sun.reflect") &&
            !declaringClass.startsWith("com.android.internal")) {
            emit("Method.invoke", {
                method: methodName,
                declaringClass: declaringClass
            });
        }
        return this.invoke(receiver, args);
    };

    // ── Session summary on unload ───────────────────────────────────────────
    Script.bindExport('getSummary', function () {
        return JSON.stringify({
            type: "session_summary",
            duration_ms: Date.now() - startTime,
            total_events: events.length,
            hook_counts: events.reduce(function (acc, e) {
                acc[e.hook] = (acc[e.hook] || 0) + 1;
                return acc;
            }, {})
        });
    });

    send(JSON.stringify({
        type: "hook_loaded",
        hooks: ["DexClassLoader", "Class.forName", "ClassLoader.loadClass", "Method.invoke"],
        timestamp: new Date().toISOString()
    }));
});
