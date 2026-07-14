Pod::Spec.new do |s|
  s.name             = 'demo_core'
  s.version          = '0.0.1'
  s.summary          = '模拟核心 SDK 的 Flutter 插件（含 Swift + ObjC）'
  s.description      = 'Demo core plugin with planted vulnerabilities for MAS static scan CI.'
  s.homepage         = 'https://example.com'
  s.license          = { :file => '../LICENSE' }
  s.author           = { 'demo' => 'demo@example.com' }
  s.source           = { :path => '.' }
  s.source_files     = 'Classes/**/*'
  s.dependency 'Flutter'
  s.platform = :ios, '12.0'
  s.swift_version = '5.0'
end
