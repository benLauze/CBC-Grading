import React, { useEffect, useRef, useState } from "react";
import { View, Text, Image, TouchableOpacity, StyleSheet, ScrollView, Animated, SafeAreaView, Dimensions } from "react-native";
import { colors, GRADE_CONFIG } from "../theme";

const { width: W } = Dimensions.get("window");
const TABS = ["grade", "price", "population"];

export default function ResultsScreen({ navigation, route }) {
  const { result, frontImage, backImage } = route?.params || {};
  const [activeTab, setActiveTab] = useState("grade");
  const fadeAnim  = useRef(new Animated.Value(0)).current;
  const scaleAnim = useRef(new Animated.Value(0.8)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim,  { toValue: 1, duration: 500, useNativeDriver: true }),
      Animated.spring(scaleAnim, { toValue: 1, tension: 60, friction: 7, useNativeDriver: true }),
    ]).start();
  }, []);

  if (!result) return null;
  const gradeInfo = GRADE_CONFIG[result.grade] || GRADE_CONFIG[6];

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView showsVerticalScrollIndicator={false}>

        {/* Card images */}
        <Animated.View style={[styles.imagesRow, { opacity: fadeAnim }]}>
          {[frontImage, backImage].map((img, i) => (
            <View key={i} style={styles.cardImageWrap}>
              <Image source={{ uri: img }} style={styles.cardImage} resizeMode="cover" />
              <View style={styles.cardImageLabel}>
                <Text style={styles.cardImageLabelText}>{i === 0 ? "FRONT" : "BACK"}</Text>
              </View>
            </View>
          ))}
        </Animated.View>

        {/* Identity */}
        <Animated.View style={[styles.section, { opacity: fadeAnim }]}>
          <Text style={styles.cardName}>{result.name}</Text>
          <Text style={styles.cardSet}>{result.set}  ·  #{result.number}</Text>
          <View style={styles.rarityBadge}>
            <Text style={styles.rarityBadgeText}>{result.rarity?.toUpperCase()}</Text>
          </View>
        </Animated.View>

        {/* Grade */}
        <Animated.View style={[styles.gradeBadgeWrap, { transform: [{ scale: scaleAnim }] }]}>
          <View style={[styles.gradeBadge, { borderColor: gradeInfo.color }]}>
            <View style={styles.gradeBadgeLeft}>
              <Text style={styles.gradeEyebrow}>CBC GRADE</Text>
              <Text style={[styles.gradeNumber, { color: gradeInfo.color }]}>{result.grade}</Text>
              <Text style={[styles.gradeLabel, { color: gradeInfo.color }]}>{gradeInfo.label}</Text>
            </View>
            <View style={styles.subgradesWrap}>
              {Object.entries(result.subgrades || {}).map(([k, v]) => (
                <View key={k} style={styles.subgradeRow}>
                  <Text style={styles.subgradeKey}>{k}</Text>
                  <View style={styles.subgradeBar}>
                    <View style={[styles.subgradeFill, { width: `${(v / 10) * 100}%` }]} />
                  </View>
                  <Text style={styles.subgradeVal}>{v}</Text>
                </View>
              ))}
            </View>
          </View>
        </Animated.View>

        {/* Tabs */}
        <View style={styles.tabBar}>
          {TABS.map(tab => (
            <TouchableOpacity key={tab} style={[styles.tab, activeTab === tab && styles.tabActive]} onPress={() => setActiveTab(tab)}>
              <Text style={[styles.tabText, activeTab === tab && styles.tabTextActive]}>
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        <View style={styles.tabContent}>

          {activeTab === "grade" && (
            <View style={styles.tabPane}>
              {Object.entries(result.subgrades || {}).map(([k, v]) => (
                <View key={k} style={styles.detailRow}>
                  <Text style={styles.detailKey}>{k.charAt(0).toUpperCase() + k.slice(1)}</Text>
                  <Text style={[styles.detailVal, { color: v >= 9 ? colors.brandTeal : v >= 7 ? colors.gold : "#CD7F32" }]}>{v}</Text>
                </View>
              ))}
            </View>
          )}

          {activeTab === "price" && (
            <View style={styles.tabPane}>
              <View style={styles.priceGrid}>
                <View style={styles.priceCard}>
                  <Text style={styles.priceLabel}>MARKET AVG</Text>
                  <Text style={[styles.priceValue, { color: colors.brandTeal }]}>${result.price?.market?.toFixed(2)}</Text>
                </View>
                <View style={styles.priceCard}>
                  <Text style={styles.priceLabel}>GRADE {result.grade}</Text>
                  <Text style={styles.priceValue}>${result.price?.market?.toFixed(2)}</Text>
                </View>
              </View>
              <View style={styles.rangeCard}>
                <Text style={styles.panelLabel}>Recent sale range</Text>
                <View style={styles.rangeRow}>
                  <Text style={styles.rangeEnd}>${result.price?.low?.toFixed(2)}</Text>
                  <View style={styles.rangeTrack}>
                    <View style={styles.rangeFill} />
                    <View style={styles.rangeThumb} />
                  </View>
                  <Text style={styles.rangeEnd}>${result.price?.high?.toFixed(2)}</Text>
                </View>
              </View>
            </View>
          )}

          {activeTab === "population" && (
            <View style={styles.tabPane}>
              <View style={styles.priceGrid}>
                <View style={styles.priceCard}>
                  <Text style={styles.priceLabel}>TOTAL POP</Text>
                  <Text style={[styles.priceValue, { color: colors.brandPurple }]}>{result.population?.total?.toLocaleString()}</Text>
                </View>
                <View style={styles.priceCard}>
                  <Text style={styles.priceLabel}>GRADE {result.grade}</Text>
                  <Text style={styles.priceValue}>{result.population?.thisGrade}</Text>
                </View>
              </View>
              <View style={styles.rangeCard}>
                <Text style={styles.panelLabel}>Grade distribution</Text>
                {[10, 9, 8, 7].map(g => {
                  const count = g === result.grade ? result.population.thisGrade : Math.round(result.population.total * [0.08, 0.145, 0.35, 0.22][10 - g]);
                  const pct = Math.round((count / result.population.total) * 100);
                  return (
                    <View key={g} style={styles.popRow}>
                      <Text style={[styles.popGrade, { color: GRADE_CONFIG[g]?.color || "#888" }]}>{g}</Text>
                      <View style={styles.popTrack}>
                        <View style={[styles.popFill, { width: `${pct}%`, backgroundColor: GRADE_CONFIG[g]?.color || "#555", opacity: g === result.grade ? 1 : 0.35 }]} />
                      </View>
                      <Text style={styles.popPct}>{pct}%</Text>
                    </View>
                  );
                })}
              </View>
            </View>
          )}

        </View>

        {/* Actions */}
        <View style={styles.actions}>
          <TouchableOpacity style={styles.secondaryBtn} onPress={() => navigation.navigate("Home", {})}>
            <Text style={styles.secondaryBtnText}>Scan New Card</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.primaryBtn}>
            <Text style={styles.primaryBtnText}>Save to Collection</Text>
          </TouchableOpacity>
        </View>

      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bgDeep },
  imagesRow: { flexDirection: "row", justifyContent: "center", gap: 12, padding: 24, backgroundColor: colors.bgCard },
  cardImageWrap: { width: (W - 72) / 2, borderRadius: 10, overflow: "hidden", borderWidth: 1, borderColor: colors.bgBorder },
  cardImage: { width: "100%", aspectRatio: 3 / 4 },
  cardImageLabel: { backgroundColor: "rgba(0,0,0,0.7)", paddingVertical: 4, alignItems: "center" },
  cardImageLabelText: { color: colors.textMuted, fontSize: 10, letterSpacing: 1.5 },
  section: { padding: 20, gap: 4 },
  cardName: { color: colors.textPrimary, fontSize: 22, fontWeight: "700" },
  cardSet: { color: colors.textSecondary, fontSize: 13 },
  rarityBadge: { alignSelf: "flex-start", marginTop: 6, backgroundColor: "rgba(123,94,167,0.18)", borderWidth: 1, borderColor: "rgba(123,94,167,0.4)", borderRadius: 6, paddingHorizontal: 10, paddingVertical: 3 },
  rarityBadgeText: { color: "#b09fd4", fontSize: 11, letterSpacing: 1 },
  gradeBadgeWrap: { paddingHorizontal: 20, paddingVertical: 16 },
  gradeBadge: { flexDirection: "row", alignItems: "center", gap: 20, backgroundColor: colors.bgCard, borderWidth: 2, borderRadius: 16, padding: 18 },
  gradeBadgeLeft: { alignItems: "center", minWidth: 72 },
  gradeEyebrow: { color: colors.textMuted, fontSize: 9, letterSpacing: 2, marginBottom: 2 },
  gradeNumber: { fontSize: 56, fontWeight: "700", lineHeight: 60 },
  gradeLabel: { fontSize: 10, fontWeight: "700", letterSpacing: 2 },
  subgradesWrap: { flex: 1, gap: 8 },
  subgradeRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  subgradeKey: { color: colors.textMuted, fontSize: 11, width: 60, textTransform: "capitalize" },
  subgradeBar: { flex: 1, height: 4, backgroundColor: colors.bgBorder, borderRadius: 2 },
  subgradeFill: { height: "100%", backgroundColor: colors.brandTeal, borderRadius: 2 },
  subgradeVal: { color: colors.textSecondary, fontSize: 11, width: 24, textAlign: "right" },
  tabBar: { flexDirection: "row", borderBottomWidth: 1, borderBottomColor: colors.bgBorder, marginHorizontal: 20 },
  tab: { flex: 1, paddingVertical: 12, alignItems: "center", borderBottomWidth: 2, borderBottomColor: "transparent" },
  tabActive: { borderBottomColor: colors.brandTeal },
  tabText: { color: colors.textMuted, fontSize: 12, letterSpacing: 1, textTransform: "uppercase" },
  tabTextActive: { color: colors.brandTeal },
  tabContent: { paddingHorizontal: 20, paddingTop: 16 },
  tabPane: { gap: 12 },
  panelLabel: { color: colors.textMuted, fontSize: 11, letterSpacing: 1, marginBottom: 4 },
  detailRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", padding: 12, backgroundColor: colors.bgCard, borderRadius: 8, borderWidth: 1, borderColor: colors.bgBorder },
  detailKey: { color: "#ccc", fontSize: 14 },
  detailVal: { fontSize: 18, fontWeight: "700" },
  priceGrid: { flexDirection: "row", gap: 10 },
  priceCard: { flex: 1, backgroundColor: colors.bgCard, borderWidth: 1, borderColor: colors.bgBorder, borderRadius: 8, padding: 14, alignItems: "center", gap: 4 },
  priceLabel: { color: colors.textMuted, fontSize: 10, letterSpacing: 1 },
  priceValue: { color: colors.textPrimary, fontSize: 20, fontWeight: "700" },
  rangeCard: { backgroundColor: colors.bgCard, borderWidth: 1, borderColor: colors.bgBorder, borderRadius: 8, padding: 14, gap: 10 },
  rangeRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  rangeEnd: { color: colors.textSecondary, fontSize: 12 },
  rangeTrack: { flex: 1, height: 6, backgroundColor: colors.bgBorder, borderRadius: 3, justifyContent: "center" },
  rangeFill: { position: "absolute", left: "15%", right: "12%", height: "100%", backgroundColor: colors.brandTeal, borderRadius: 3, opacity: 0.6 },
  rangeThumb: { position: "absolute", left: "50%", width: 14, height: 14, borderRadius: 7, backgroundColor: colors.brandTeal, borderWidth: 2, borderColor: colors.bgDeep, marginLeft: -7 },
  popRow: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 4 },
  popGrade: { fontSize: 13, fontWeight: "700", width: 18 },
  popTrack: { flex: 1, height: 6, backgroundColor: colors.bgBorder, borderRadius: 3, overflow: "hidden" },
  popFill: { height: "100%", borderRadius: 3 },
  popPct: { color: colors.textMuted, fontSize: 11, width: 28, textAlign: "right" },
  actions: { flexDirection: "row", gap: 10, padding: 20, paddingBottom: 36 },
  secondaryBtn: { flex: 1, paddingVertical: 14, borderRadius: 10, borderWidth: 1, borderColor: colors.bgBorder, alignItems: "center" },
  secondaryBtnText: { color: colors.textSecondary, fontSize: 14 },
  primaryBtn: { flex: 2, paddingVertical: 14, borderRadius: 10, backgroundColor: colors.brandPurple, alignItems: "center" },
  primaryBtnText: { color: "#fff", fontSize: 14, fontWeight: "700" },
});
