package com.gathin.tvhome;

/** Tracks HOME versus an ordinary app launch independently of temporary settings/input intents. */
final class HomeEntry {
    private boolean home;

    void launch(boolean homeCategory) {
        home = homeCategory;
    }

    boolean isHome() {
        return home;
    }

    boolean canExit(boolean ordinaryAppBackEnabled) {
        return ordinaryAppBackEnabled && !home;
    }
}
