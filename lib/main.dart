import 'package:flutter/material.dart';

void main() => runApp(const SlsaDemoApp());

class SlsaDemoApp extends StatelessWidget {
  const SlsaDemoApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Flutter SLSA Demo',
      home: Scaffold(
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: const [
              Icon(Icons.verified, size: 96, color: Colors.green),
              SizedBox(height: 16),
              Text(
                'Flutter + fastlane + SLSA',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
              SizedBox(height: 8),
              Text(
                '这个产物由 GitHub Actions 构建，\n并附带 SLSA Build L3 provenance。',
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
