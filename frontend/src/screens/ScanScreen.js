import React, { useState } from "react";
import { View, Text, TouchableOpacity, StyleSheet, SafeAreaView } from "react-native";
import ScanViewfinder from "../components/ScanViewfinder";
import { colors } from "../theme";

export default function ScanScreen({ navigation, route }) {
  const { side, existingFront, existingBack } = route?.params || {};
  const isFront = side === "front";
  const [capturedImage, setCapturedImage] = useState(isFront ? existingFront || null : existingBack || null);

  const handleContinue = () => {
    const frontImage = isFront ? capturedImage : existingFront;
    const backImage  = isFront ? existingBack  : capturedImage;
    if (isFront) {
      navigation.navigate("ScanBack", { side: "back", existingFront: capturedImage, existingBack });
    } else {
      navigation.navigate("Processing", { frontImage, backImage });
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.container}>
        <View style={styles.header}>
          <TouchableOpacity style={styles.backBtn} onPress={() => navigation.navigate("Home", { frontImage: existingFront, backImage: existingBack })}>
            <Text style={styles.backIcon}>‹</Text>
          </TouchableOpacity>
          <View>
            <Text style={styles.stepLabel}>{isFront ? "Step 1 of 2" : "Step 2 of 2"}</Text>
            <Text style={styles.screenTitle}>{isFront ? "Scan Card Front" : "Scan Card Back"}</Text>
          </View>
        </View>

        <View style={styles.viewfinderWrap}>
          <ScanViewfinder
            label={isFront
              ? "Position the front of the card inside the frame. Ensure full card is visible and well-lit."
              : "Flip the card and position the back inside the frame."}
            onCapture={setCapturedImage}
            capturedImage={capturedImage}
            onRetake={() => setCapturedImage(null)}
          />
        </View>

        {capturedImage && (
          <TouchableOpacity style={styles.continueBtn} onPress={handleContinue} activeOpacity={0.85}>
            <Text style={styles.continueBtnText}>{isFront ? "Continue to Back  →" : "Done  →"}</Text>
          </TouchableOpacity>
        )}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bgDeep },
  container: { flex: 1, paddingHorizontal: 20, paddingBottom: 32, gap: 24 },
  header: { flexDirection: "row", alignItems: "center", gap: 14, paddingTop: 12 },
  backBtn: { width: 36, height: 36, borderRadius: 10, backgroundColor: colors.bgCard, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: colors.bgBorder },
  backIcon: { color: colors.textPrimary, fontSize: 22, lineHeight: 26 },
  stepLabel: { color: colors.brandTeal, fontSize: 11, letterSpacing: 2, textTransform: "uppercase", marginBottom: 2 },
  screenTitle: { color: colors.textPrimary, fontSize: 22, fontWeight: "700" },
  viewfinderWrap: { flex: 1, justifyContent: "center" },
  continueBtn: { width: "100%", paddingVertical: 16, borderRadius: 12, backgroundColor: colors.brandPurple, alignItems: "center" },
  continueBtnText: { color: "#fff", fontSize: 16, fontWeight: "700", letterSpacing: 0.8 },
});
