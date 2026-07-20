import React, { useEffect, useRef, useState } from "react";
import { View, Text, StyleSheet, Animated, Easing, SafeAreaView } from "react-native";
import { colors } from "../theme";
//CHANGE MADE
import { processCard } from "../api";

const STEPS = [
  "Analyzing card surfaces...",
  "Identifying set & edition...",
  "Checking market prices...",
  "Grading condition...",
];

export default function ProcessingScreen({ navigation, route }) {
  const { frontImage, backImage } = route?.params || {};
  const [currentStep, setCurrentStep] = useState(0);
  const [error, setError] = useState(null);
  const rotateAnim = useRef(new Animated.Value(0)).current;
  const progressAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.loop(
      Animated.timing(rotateAnim, { toValue: 1, duration: 1400, easing: Easing.linear, useNativeDriver: true })
    ).start();
  }, []);

  //useEffect(() => {
    //CHANGE MADE
    //const timers = STEPS.map((_, i) => setTimeout(() => setCurrentStep(i), i * 1100));
    //return () => timers.forEach(clearTimeout);
  //}, []);

  // Change Made
  useEffect(() => {
    let step = 0;
    const interval = setInterval(() => {
      step++;
      if (step < STEPS.length) {
        setCurrentStep(step);
      } else {
        clearInterval(interval);
      }
    }, 1100);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    Animated.timing(progressAnim, { toValue: 1, duration: 4200, easing: Easing.out(Easing.quad), useNativeDriver: false }).start();
  }, []);

  useEffect(() => {
    const run = async () => {
      try {
        // ─────────────────────────────────────────────────────────
        // BACKEND INTEGRATION — Replace mock with your API call:
        //
        // const formData = new FormData();
        // formData.append('front', { uri: frontImage, name: 'front.jpg', type: 'image/jpeg' });
        // formData.append('back',  { uri: backImage,  name: 'back.jpg',  type: 'image/jpeg' });
        // const res = await fetch('https://your-api.com/grade', { method: 'POST', body: formData });
        // const result = await res.json();
        // ─────────────────────────────────────────────────────────

        //await new Promise(r => setTimeout(r, 4500)); // mock delay

        //const result = {
          //name: "Charizard VMAX",
          //set: "Sword & Shield — Champion's Path",
          //setCode: "SWSH035",
          //number: "074/073",
          //rarity: "Secret Rare",
          //grade: 9,
          //subgrades: { centering: 9.5, corners: 9.0, edges: 8.5, surface: 9.5 },
          //price: { market: 189.99, low: 145.00, high: 250.00 },
          //population: { total: 2847, thisGrade: 412 },
        //};

        //navigation.navigate("Results", { result, frontImage, backImage });

        //CHANGE MADE
        const result = await processCard(frontImage, backImage);
        navigation.navigate("Results", { result, frontImage, backImage });

      } catch (err) {
        setError(err.message || "Analysis failed. Please try again.");
      }
    };
    run();
  }, []);

  const spin = rotateAnim.interpolate({ inputRange: [0, 1], outputRange: ["0deg", "360deg"] });
  const progressWidth = progressAnim.interpolate({ inputRange: [0, 1], outputRange: ["0%", "100%"] });

  if (error) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.errorContainer}>
          <Text style={{ fontSize: 40 }}>⚠️</Text>
          <Text style={styles.errorTitle}>Analysis Failed</Text>
          <Text style={styles.errorMsg}>{error}</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.container}>
        <View style={styles.spinnerWrap}>
          <Animated.View style={[styles.spinnerRing, { transform: [{ rotate: spin }] }]} />
          <View style={styles.spinnerCenter}><Text style={styles.spinnerLabel}>CBC</Text></View>
        </View>

        <View style={styles.textGroup}>
          <Text style={styles.analyzingLabel}>Analyzing</Text>
          <Text style={styles.stepText}>{STEPS[currentStep]}</Text>
        </View>

        <View style={styles.progressTrack}>
          <Animated.View style={[styles.progressFill, { width: progressWidth }]} />
        </View>

        <View style={styles.checklist}>
          {STEPS.map((step, i) => (
            <View key={i} style={styles.checkRow}>
              <View style={[styles.checkDot, i <= currentStep && styles.checkDotDone]}>
                {i <= currentStep && <Text style={styles.checkMark}>✓</Text>}
              </View>
              <Text style={[styles.checkText, i <= currentStep && styles.checkTextDone]}>{step}</Text>
            </View>
          ))}
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bgDeep },
  container: { flex: 1, alignItems: "center", justifyContent: "center", paddingHorizontal: 32, gap: 28 },
  spinnerWrap: { width: 100, height: 100, alignItems: "center", justifyContent: "center" },
  spinnerRing: { position: "absolute", width: 100, height: 100, borderRadius: 50, borderWidth: 3, borderColor: "transparent", borderTopColor: colors.brandTeal, borderRightColor: colors.brandPurple },
  spinnerCenter: { width: 80, height: 80, borderRadius: 40, backgroundColor: colors.bgCard, borderWidth: 1, borderColor: colors.bgBorder, alignItems: "center", justifyContent: "center" },
  spinnerLabel: { color: colors.textSecondary, fontSize: 13, fontWeight: "800", letterSpacing: 2 },
  textGroup: { alignItems: "center", gap: 6 },
  analyzingLabel: { color: colors.brandTeal, fontSize: 11, letterSpacing: 2.5, textTransform: "uppercase" },
  stepText: { color: colors.textPrimary, fontSize: 16, fontWeight: "600", textAlign: "center" },
  progressTrack: { width: "100%", height: 4, backgroundColor: colors.bgBorder, borderRadius: 2, overflow: "hidden" },
  progressFill: { height: "100%", backgroundColor: colors.brandTeal, borderRadius: 2 },
  checklist: { width: "100%", gap: 12 },
  checkRow: { flexDirection: "row", alignItems: "center", gap: 12 },
  checkDot: { width: 22, height: 22, borderRadius: 11, backgroundColor: colors.bgCard, borderWidth: 1, borderColor: colors.bgBorder, alignItems: "center", justifyContent: "center" },
  checkDotDone: { backgroundColor: colors.brandTeal, borderColor: colors.brandTeal },
  checkMark: { color: "#003d33", fontSize: 11, fontWeight: "800" },
  checkText: { color: colors.textMuted, fontSize: 13 },
  checkTextDone: { color: colors.textSecondary },
  errorContainer: { flex: 1, alignItems: "center", justifyContent: "center", gap: 12, padding: 32 },
  errorTitle: { color: colors.textPrimary, fontSize: 20, fontWeight: "700" },
  errorMsg: { color: colors.textSecondary, fontSize: 14, textAlign: "center", lineHeight: 22 },
});
