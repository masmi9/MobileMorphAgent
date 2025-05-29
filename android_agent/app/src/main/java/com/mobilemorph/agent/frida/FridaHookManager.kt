socket.on("load_frida_script") { args ->
    val jsCode = args[0].asJsonObject["script"].asString
    val hookPath = File(context.cacheDir, "frida_hook.js")
    hookPath.writeText(jsCode)

    val cmd = arrayOf("frida", "-U", "-n", "com.target.app", "-l", hookPath.absolutePath, "--no-pause")
    Runtime.getRuntime().exec(cmd)
}
