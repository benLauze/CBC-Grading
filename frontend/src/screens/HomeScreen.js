import React from "react";
import {
  View, Text, TouchableOpacity, StyleSheet, ScrollView, SafeAreaView,
} from "react-native";
import { colors } from "../theme";

export default function HomeScreen({ navigation, route }) {
  const frontImage = route?.params?.frontImage || null;
  const backImage  = route?.params?.backImage  || null;
  const bothScanned = frontImage && backImage;

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.content}>

        {/* Header */}
        <View style={styles.header}>
          <View style={styles.logoMark}><Text style={styles.logoText}>CBC</Text></View>
          <Text style={styles.appName}>CBC Grading</Text>
        </View>

        {/* Hero */}
        <View style={styles.hero}>
          <Text style={styles.heroTitle}>Grade Your Card</Text>
          <Text style={styles.heroSub}>
            Scan both sides of your Pokémon card for an instant grade, set ID, and market price.
          </Text>
        </View>

        {/* Scan steps */}
        <View style={styles.steps}>
          {[
            { label: "Scan card front", desc: frontImage ? "Captured — tap to retake" : "Card art, name & number", done: !!frontImage, screen: "ScanFront" },
            { label: "Scan card back",  desc: backImage  ? "Captured — tap to retake" : "Card reverse side",      done: !!backImage,  screen: "ScanBack"  },
          ].map((step, i) => (
            <TouchableOpacity
              key={i}
              style={[styles.stepRow, step.done && styles.stepRowDone]}
              onPress={() => navigation.navigate(step.screen, { side: i === 0 ? "front" : "back", existingFront: frontImage, existingBack: backImage })}
              activeOpacity={0.75}
            >
              <View style={[styles.stepIcon, step.done && styles.stepIconDone]}>
                <Text style={{ fontSize: 18 }}>{step.done ? "✓" : "📷"}</Text>
              </View>
              <View style={styles.stepText}>
                <Text style={[styles.stepLabel, step.done && styles.stepLabelDone]}>{step.label}</Text>
                <Text style={styles.stepDesc}>{step.desc}</Text>
              </View>
              <Text style={{ color: colors.textMuted, fontSize: 20 }}>›</Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* CTA */}
        <TouchableOpacity
          style={[styles.ctaBtn, !bothScanned && styles.ctaBtnDisabled]}
          onPress={() => bothScanned && navigation.navigate("Processing", { frontImage, backImage })}
          activeOpacity={bothScanned ? 0.85 : 1}
        >
          <Text style={[styles.ctaBtnText, !bothScanned && styles.ctaBtnTextDisabled]}>
            {bothScanned ? "Analyze Card  →" : "Scan both sides to continue"}
          </Text>
        </TouchableOpacity>

        {/* Info */}
        <View style={styles.infoCard}>
          <Text style={styles.infoTitle}>What you'll get</Text>
          {[["Set & Edition", colors.brandPurple], ["Market Price", colors.brandTeal], ["CBC Grade (1–10)", colors.gold]].map(([label, dot]) => (
            <View key={label} style={styles.infoRow}>
              <View style={[styles.infoDot, { backgroundColor: dot }]} />
              <Text style={styles.infoLabel}>{label}</Text>
            </View>
          ))}
        </View>

      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bgDeep },
  content: { paddingHorizontal: 20, paddingBottom: 40, gap: 24 },
  header: { flexDirection: "row", alignItems: "center", gap: 10, paddingTop: 20 },
  logoMark: { width: 36, height: 36, borderRadius: 9, backgroundColor: colors.brandPurple, alignItems: "center", justifyContent: "center" },
  logoText: { color: "#fff", fontSize: 12, fontWeight: "800", letterSpacing: 1 },
  appName: { color: colors.textPrimary, fontSize: 20, fontWeight: "700" },
  hero: { gap: 8 },
  heroTitle: { color: colors.textPrimary, fontSize: 30, fontWeight: "700" },
  heroSub: { color: colors.textSecondary, fontSize: 14, lineHeight: 22 },
  steps: { gap: 12 },
  stepRow: { flexDirection: "row", alignItems: "center", gap: 14, padding: 16, backgroundColor: colors.bgCard, borderRadius: 12, borderWidth: 1, borderColor: colors.bgBorder },
  stepRowDone: { borderColor: "rgba(0,201,167,0.35)", backgroundColor: "rgba(0,201,167,0.05)" },
  stepIcon: { width: 42, height: 42, borderRadius: 10, backgroundColor: colors.bgBorder, alignItems: "center", justifyContent: "center" },
  stepIconDone: { backgroundColor: "rgba(0,201,167,0.15)" },
  stepText: { flex: 1 },
  stepLabel: { color: "#ccc", fontSize: 14, fontWeight: "600", marginBottom: 2 },
  stepLabelDone: { color: colors.brandTeal },
  stepDesc: { color: colors.textMuted, fontSize: 12 },
  ctaBtn: { width: "100%", paddingVertical: 16, borderRadius: 12, backgroundColor: colors.brandPurple, alignItems: "center" },
  ctaBtnDisabled: { backgroundColor: colors.bgBorder },
  ctaBtnText: { color: "#fff", fontSize: 16, fontWeight: "700", letterSpacing: 0.8 },
  ctaBtnTextDisabled: { color: colors.textMuted },
  infoCard: { backgroundColor: colors.bgCard, borderRadius: 12, borderWidth: 1, borderColor: colors.bgBorder, padding: 16, gap: 10 },
  infoTitle: { color: colors.textMuted, fontSize: 11, letterSpacing: 1.5, textTransform: "uppercase", marginBottom: 2 },
  infoRow: { flexDirection: "row", alignItems: "center", gap: 10 },
  infoDot: { width: 7, height: 7, borderRadius: 4 },
  infoLabel: { color: colors.textSecondary, fontSize: 13 },
});
