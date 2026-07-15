import React, { useRef, useState, useEffect } from "react";
import { View, Text, TouchableOpacity, Image, StyleSheet, Animated, Easing, Dimensions } from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";
import { colors } from "../theme";

const { width: W } = Dimensions.get("window");
const FRAME_W = W - 40;
const FRAME_H = FRAME_W * (4 / 3);

export default function ScanViewfinder({ label, onCapture, capturedImage, onRetake }) {
  const cameraRef = useRef(null);
  const [permission, requestPermission] = useCameraPermissions();
  const scanAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (capturedImage) return;
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(scanAnim, { toValue: 1, duration: 2200, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
        Animated.timing(scanAnim, { toValue: 0, duration: 2200, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [capturedImage]);

  const scanY = scanAnim.interpolate({ inputRange: [0, 1], outputRange: [0, FRAME_H - 2] });

  const handleCapture = async () => {
    if (!cameraRef.current) return;
    try {
      const photo = await cameraRef.current.takePictureAsync({ quality: 0.85 });
      onCapture(photo.uri);
    } catch (err) {
      console.error("Capture failed:", err);
    }
  };

  if (capturedImage) {
    return (
      <View style={styles.container}>
        <View style={styles.capturedFrame}>
          <Image source={{ uri: capturedImage }} style={styles.capturedImage} resizeMode="cover" />
          <View style={styles.capturedBadge}><Text style={styles.capturedBadgeText}>✓  CAPTURED</Text></View>
        </View>
        <TouchableOpacity style={styles.retakeBtn} onPress={onRetake}>
          <Text style={styles.retakeBtnText}>Retake Photo</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (!permission?.granted) {
    return (
      <View style={styles.container}>
        <View style={[styles.frame, styles.permFrame]}>
          <Text style={{ fontSize: 40 }}>📷</Text>
          <Text style={styles.permText}>Camera access required to scan cards.</Text>
          <TouchableOpacity style={styles.permBtn} onPress={requestPermission}>
            <Text style={styles.permBtnText}>Allow Camera</Text>
          </TouchableOpacity>
        </View>
        <Text style={styles.label}>{label}</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.frame}>
        <CameraView ref={cameraRef} style={StyleSheet.absoluteFill} facing="back" autofocus="on" />
        <Animated.View style={[styles.scanLine, { transform: [{ translateY: scanY }] }]} pointerEvents="none" />
        {/* Corner brackets */}
        {[{ t: 10, l: 10 }, { t: 10, r: 10 }, { b: 10, l: 10 }, { b: 10, r: 10 }].map((pos, i) => (
          <View key={i} style={[styles.corner, pos]} pointerEvents="none">
            <View style={[styles.cH, i % 2 === 1 && { alignSelf: "flex-end" }]} />
            <View style={[styles.cV, i % 2 === 1 && { alignSelf: "flex-end" }, i >= 2 && { order: -1 }]} />
          </View>
        ))}
      </View>
      <TouchableOpacity style={styles.shutter} onPress={handleCapture} activeOpacity={0.8}>
        <View style={styles.shutterInner} />
      </TouchableOpacity>
      <Text style={styles.label}>{label}</Text>
    </View>
  );
}

const C = colors.brandTeal;
const styles = StyleSheet.create({
  container: { alignItems: "center", gap: 20 },
  frame: { width: FRAME_W, height: FRAME_H, borderRadius: 14, overflow: "hidden", backgroundColor: colors.bgCard },
  permFrame: { alignItems: "center", justifyContent: "center", gap: 12, padding: 24 },
  permText: { color: colors.textSecondary, fontSize: 14, textAlign: "center" },
  permBtn: { marginTop: 8, backgroundColor: colors.brandPurple, paddingHorizontal: 20, paddingVertical: 10, borderRadius: 8 },
  permBtnText: { color: "#fff", fontSize: 14, fontWeight: "600" },
  scanLine: { position: "absolute", left: "8%", right: "8%", height: 2, backgroundColor: C, opacity: 0.75 },
  corner: { position: "absolute", width: 36, height: 36 },
  cH: { width: 28, height: 2.5, backgroundColor: C, borderRadius: 1 },
  cV: { width: 2.5, height: 28, backgroundColor: C, borderRadius: 1 },
  shutter: { width: 68, height: 68, borderRadius: 34, borderWidth: 3, borderColor: "rgba(255,255,255,0.2)", alignItems: "center", justifyContent: "center" },
  shutterInner: { width: 52, height: 52, borderRadius: 26, backgroundColor: C },
  label: { color: colors.textMuted, fontSize: 12, textAlign: "center", paddingHorizontal: 20, lineHeight: 18 },
  capturedFrame: { width: FRAME_W, borderRadius: 14, overflow: "hidden" },
  capturedImage: { width: FRAME_W, height: FRAME_H },
  capturedBadge: { position: "absolute", top: 12, right: 12, backgroundColor: C, borderRadius: 20, paddingHorizontal: 12, paddingVertical: 4 },
  capturedBadgeText: { color: "#003d33", fontSize: 11, fontWeight: "700", letterSpacing: 1 },
  retakeBtn: { borderWidth: 1, borderColor: "rgba(255,255,255,0.15)", borderRadius: 8, paddingHorizontal: 20, paddingVertical: 8 },
  retakeBtnText: { color: colors.textSecondary, fontSize: 13 },
});
