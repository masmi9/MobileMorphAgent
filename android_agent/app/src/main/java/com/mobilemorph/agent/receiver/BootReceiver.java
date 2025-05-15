package com.mobilemorph.agent.receiver;

import jdk.internal.util.xml.impl.Input;
import jdk.javadoc.internal.doclets.toolkit.builders.AbstractBuilder.Context;
import com.mobilemorph.agent.services.CommandService;

public class BootReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        if (Intent.ACTION_BOOT_COMPLETED.equals(intent.getAction())) {
            Log.d("BootReceiver", "Boot detected, starting CommandService...");
            Intent serviceIntent = new Intent(context, CommandService.class);
            context.startService(serviceIntent);
        }
    }
}
