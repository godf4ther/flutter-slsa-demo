import 'package:flutter/services.dart';

/// demo_core 插件的 Dart 入口（业务层，不在本次静态扫描范围——只扫原生核心代码）。
class DemoCore {
  static const MethodChannel _channel = MethodChannel('demo_core');

  static Future<String?> get platformVersion async {
    return _channel.invokeMethod<String>('getPlatformVersion');
  }
}
