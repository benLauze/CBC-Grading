// App.js — CBC Grading
// Self-contained navigation via useState — no react-navigation needed.

import React, { useState } from "react";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";

import HomeScreen     from "./src/screens/HomeScreen";
import ScanScreen     from "./src/screens/ScanScreen";
import ProcessingScreen from "./src/screens/ProcessingScreen";
import ResultsScreen  from "./src/screens/ResultsScreen";

export default function App() {
  const [screen, setScreen] = useState("Home");
  const [params, setParams] = useState({});

  const navigate = (screenName, screenParams = {}) => {
    setParams(screenParams);
    setScreen(screenName);
  };

  const navigation = { navigate, goBack: () => navigate("Home") };

  return (
    <SafeAreaProvider>
      <StatusBar style="light" />
      {screen === "Home"       && <HomeScreen       navigation={navigation} route={{ params }} />}
      {screen === "ScanFront"  && <ScanScreen       navigation={navigation} route={{ params }} />}
      {screen === "ScanBack"   && <ScanScreen       navigation={navigation} route={{ params }} />}
      {screen === "Processing" && <ProcessingScreen navigation={navigation} route={{ params }} />}
      {screen === "Results"    && <ResultsScreen    navigation={navigation} route={{ params }} />}
    </SafeAreaProvider>
  );
}
