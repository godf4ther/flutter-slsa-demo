import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_slsa_demo/main.dart';

void main() {
  testWidgets('渲染 SLSA 标识页', (tester) async {
    await tester.pumpWidget(const SlsaDemoApp());
    expect(find.text('Flutter + fastlane + SLSA'), findsOneWidget);
    expect(find.byIcon(Icons.verified), findsOneWidget);
  });
}
