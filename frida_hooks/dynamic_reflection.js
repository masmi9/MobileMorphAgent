Java.perform(function() {
    console.log("[*] Reflection Monitor Hook Loaded");

    // Hook DexClassLoader
    var DexClassLoader = Java.use("dalvik.system.DexClassLoader");
    DexClassLoader.$init.overload('java.lang.String', 'java.lang.String', 'java.lang.String', 'java.lang.ClassLoader')
        .implementation = function(dexPath, optimizedDir, libPath, parent) {
            console.log("[DexClassLoader] dexPath: " + dexPath);
            return this.$init(dexPath, optimizedDir, libPath, parent);
        };

    // Hook Class.forName
    var Class = Java.use("java.lang.Class");
    Class.forName.overload('java.lang.String').implementation = function(name) {
        console.log("[Class.forName] Loaded: " + name);
        return this.forName(name);
    };

    // Hook loadClass
    var ClassLoader = Java.use("java.lang.ClassLoader");
    ClassLoader.loadClass.overload('java.lang.String').implementation = function(className) {
        console.log("[loadClass] ClassLoader: " + className);
        return this.loadClass(className);
    };

    // Hook Method.invoke
    var Method = Java.use("java.lang.reflect.Method");
    Method.invoke.implementation = function(receiver, args) {
        console.log("[Method.invoke] Called: " + this.getName());
        return this.invoke(receiver, args);
    };
});